# ============================================
# COMPLETE VOTING VIEWS - REPLACE ALL in voting/views.py
# ============================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from payments.models import Payment
from .models import Election, Position, Candidate, Vote, VoterProfile, VotingSession


def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@login_required
def election_List(request):
    """Display list of all elections"""
    elections = Election.objects.all()
    
    # Auto-update election statuses
    for election in elections:
        election.auto_update_status()
    
    # Check if user has voter profile
    try:
        voter_profile = request.user.voter_profile
        has_profile = True
    except VoterProfile.DoesNotExist:
        voter_profile = None
        has_profile = False
    
    # Check payment status
    has_paid = Payment.objects.filter(
        user=request.user,
        status='success'
    ).exists()
    
    context = {
        'elections': elections,
        'voter_profile': voter_profile,
        'has_profile': has_profile,
        'has_paid': has_paid,
    }
    return render(request, 'election_List.html', context)


@login_required
def voter_registration(request):
    """Register voter with registration number"""
    # Check if already registered
    try:
        voter_profile = request.user.voter_profile
        messages.info(request, 'You are already registered!')
        return redirect('election_List')
    except VoterProfile.DoesNotExist:
        pass
    
    if request.method == 'POST':
        reg_number = request.POST.get('registration_number', '').strip().upper()
        phone = request.POST.get('phone', '').strip()
        level = request.POST.get('level', '').strip()
        
        if not reg_number:
            messages.error(request, 'Registration number is required')
            return redirect('voter_registration')
        
        try:
            # Create voter profile
            voter_profile = VoterProfile.objects.create(
                user=request.user,
                registration_number=reg_number,
                phone=phone,
                level=level,
                has_paid_dues=False,
                is_verified=False
            )
            
            messages.success(
                request,
                'Registration submitted! An admin will verify your details shortly.'
            )
            return redirect('election_List')
            
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
    
    return render(request, 'voter_registration.html')


@login_required
def election_detail(request, election_id):
    """Display election details and voting interface"""
    election = get_object_or_404(Election, id=election_id)
    election.auto_update_status()
    
    # Check voter eligibility
    try:
        voter_profile = request.user.voter_profile
    except VoterProfile.DoesNotExist:
        messages.warning(request, 'You must register as a voter first!')
        return redirect('voter_registration')
    
    # Check if voter has paid dues
    if not voter_profile.has_paid_dues:
        messages.error(
            request,
            'You must pay departmental dues before you can vote. Visit the payment page.'
        )
        return redirect('payment_page')
    
    # Check if voter is verified
    if not voter_profile.is_verified:
        messages.warning(
            request,
            'Your registration is pending admin verification. Please wait for approval.'
        )
        return redirect('election_List')
    
    # Check if already voted
    has_voted = voter_profile.has_voted_in_election(election)
    
    # Get positions and candidates
    positions = election.positions.prefetch_related('candidates').all()
    
    # Get user's votes if they've voted
    user_votes = {}
    if has_voted:
        votes = Vote.objects.filter(
            voter=request.user,
            candidate__position__election=election
        ).select_related('candidate', 'candidate__position')
        
        for vote in votes:
            user_votes[vote.candidate.position.name] = vote.candidate
    
    context = {
        'election': election,
        'positions': positions,
        'has_voted': has_voted,
        'user_votes': user_votes,
        'can_vote': election.can_vote() and not has_voted,
    }
    
    return render(request, 'election_detail.html', context)


@login_required
def cast_vote(request, election_id):
    """Process vote submission"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    election = get_object_or_404(Election, id=election_id)
    
    # Verify election is active
    if not election.can_vote():
        return JsonResponse({'error': 'Voting is not currently active'}, status=400)
    
    # Verify voter eligibility
    try:
        voter_profile = request.user.voter_profile
    except VoterProfile.DoesNotExist:
        return JsonResponse({'error': 'You must register as a voter first'}, status=403)
    
    if not voter_profile.can_vote(election):
        return JsonResponse({'error': 'You are not eligible to vote'}, status=403)
    
    # Check if already voted
    if voter_profile.has_voted_in_election(election):
        return JsonResponse({'error': 'You have already voted in this election'}, status=400)
    
    # Get candidate selections from POST data
    candidate_ids = []
    for key, value in request.POST.items():
        if key.startswith('position_'):
            if value:
                candidate_ids.append(int(value))
    
    if not candidate_ids:
        return JsonResponse({'error': 'Please select at least one candidate'}, status=400)
    
    try:
        with transaction.atomic():
            # Create voting session
            session = VotingSession.objects.create(
                voter=request.user,
                election=election,
                ip_address=get_client_ip(request)
            )
            
            # Cast votes
            votes_cast = []
            for candidate_id in candidate_ids:
                candidate = get_object_or_404(Candidate, id=candidate_id)
                
                # Verify candidate belongs to this election
                if candidate.position.election != election:
                    raise ValidationError('Invalid candidate selection')
                
                # Create vote
                vote = Vote.objects.create(
                    voter=request.user,
                    candidate=candidate,
                    ip_address=get_client_ip(request)
                )
                votes_cast.append(vote)
            
            # Mark session as completed
            session.mark_completed()
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully cast {len(votes_cast)} vote(s)!',
                'votes_count': len(votes_cast)
            })
            
    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Vote submission failed: {str(e)}'}, status=500)


@login_required
def election_results(request, election_id):
    """Display election results"""
    election = get_object_or_404(Election, id=election_id)
    
    # Check if results should be visible
    can_view = election.show_results or election.results_published or request.user.is_staff
    
    if not can_view:
        messages.warning(request, 'Results are not yet available for this election.')
        return redirect('election_detail', election_id=election_id)
    
    # Get all positions with candidates and vote counts
    positions = election.positions.prefetch_related('candidates').all()
    
    results_data = []
    total_voters = VotingSession.objects.filter(
        election=election,
        is_completed=True
    ).values('voter').distinct().count()
    
    for position in positions:
        candidates_data = []
        total_votes = position.get_total_votes()
        
        for candidate in position.get_candidates():
            vote_count = candidate.get_vote_count()
            percentage = candidate.get_vote_percentage()
            
            candidates_data.append({
                'candidate': candidate,
                'votes': vote_count,
                'percentage': percentage
            })
        
        # Sort by votes (descending)
        candidates_data.sort(key=lambda x: x['votes'], reverse=True)
        
        results_data.append({
            'position': position,
            'candidates': candidates_data,
            'total_votes': total_votes
        })
    
    context = {
        'election': election,
        'results_data': results_data,
        'total_voters': total_voters,
    }
    
    return render(request, 'eresults.html', context)


@login_required
def candidate_detail(request, candidate_id):
    """Display candidate profile (OLD VERSION - kept for compatibility)"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    context = {
        'candidate': candidate,
        'election': candidate.position.election,
    }
    
    return render(request, 'candidate_detail.html', context)


# ============================================
# ENHANCED CANDIDATE VIEWS (NEW)
# ============================================

@login_required
def enhanced_candidate_detail(request, candidate_id):
    """Enhanced candidate profile page"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    election = candidate.position.election
    
    # Increment profile views
    candidate.increment_profile_views()
    
    # Get other candidates in same position
    other_candidates = Candidate.objects.filter(
        position=candidate.position,
        is_active=True
    ).exclude(id=candidate_id)
    
    # Check if user has voted for this position
    has_voted_position = Vote.objects.filter(
        voter=request.user,
        candidate__position=candidate.position
    ).exists()
    
    # Check if user voted for this specific candidate
    user_voted_for_this = Vote.objects.filter(
        voter=request.user,
        candidate=candidate
    ).exists()
    
    # Check if user can vote
    try:
        voter_profile = request.user.voter_profile
        can_vote = (
            voter_profile.can_vote(election) and
            not has_voted_position and
            election.can_vote()
        )
    except:
        can_vote = False
    
    context = {
        'candidate': candidate,
        'election': election,
        'other_candidates': other_candidates,
        'has_voted_position': has_voted_position,
        'user_voted_for_this': user_voted_for_this,
        'can_vote': can_vote,
    }
    
    return render(request, 'candidate_profile.html', context)


@login_required
def meet_candidates(request, election_id):
    """Meet the Candidates gallery page"""
    election = get_object_or_404(Election, id=election_id)
    
    # Get filter parameters
    position_filter = request.GET.get('position', '')
    
    # Get all positions for this election
    positions = election.positions.prefetch_related('candidates').all()
    
    # Organize candidates by position
    candidates_by_position = []
    for position in positions:
        if position_filter and str(position.id) != position_filter:
            continue
            
        candidates = position.get_candidates().order_by('name')
        if candidates:
            candidates_by_position.append({
                'position': position,
                'candidates': candidates
            })
    
    context = {
        'election': election,
        'candidates_by_position': candidates_by_position,
        'positions': positions,
        'selected_position': position_filter,
    }
    
    return render(request, 'meet_candidates.html', context)


@login_required
def compare_candidates(request, election_id):
    """Compare multiple candidates side-by-side"""
    election = get_object_or_404(Election, id=election_id)
    
    # Get candidate IDs from query params
    candidate_ids = request.GET.getlist('candidates')
    
    if not candidate_ids or len(candidate_ids) < 2:
        # No candidates selected, show selection page
        positions = election.positions.prefetch_related('candidates').all()
        context = {
            'election': election,
            'positions': positions,
        }
        return render(request, 'compare_select.html', context)
    
    # Get selected candidates
    candidates = Candidate.objects.filter(
        id__in=candidate_ids,
        position__election=election,
        is_active=True
    ).select_related('position')
    
    # Check if all candidates are from same position
    positions = set(c.position for c in candidates)
    same_position = len(positions) == 1
    
    context = {
        'election': election,
        'candidates': candidates,
        'same_position': same_position,
    }
    
    return render(request, 'compare_candidates.html', context)


@login_required
def vote_for_candidate(request, candidate_id):
    """Quick vote for a specific candidate from their profile"""
    if request.method != 'POST':
        return redirect('enhanced_candidate_detail', candidate_id=candidate_id)
    
    candidate = get_object_or_404(Candidate, id=candidate_id)
    election = candidate.position.election
    
    # Verify election is active
    if not election.can_vote():
        messages.error(request, 'Voting is not currently active')
        return redirect('enhanced_candidate_detail', candidate_id=candidate_id)
    
    # Verify voter eligibility
    try:
        voter_profile = request.user.voter_profile
    except:
        messages.error(request, 'You must register as a voter first')
        return redirect('voter_registration')
    
    if not voter_profile.can_vote(election):
        messages.error(request, 'You are not eligible to vote')
        return redirect('enhanced_candidate_detail', candidate_id=candidate_id)
    
    # Check if already voted for this position
    existing_vote = Vote.objects.filter(
        voter=request.user,
        candidate__position=candidate.position
    ).exists()
    
    if existing_vote:
        messages.error(request, f'You have already voted for {candidate.position.get_name_display()}')
        return redirect('enhanced_candidate_detail', candidate_id=candidate_id)
    
    # Cast vote
    try:
        with transaction.atomic():
            # Get or create voting session
            session, created = VotingSession.objects.get_or_create(
                voter=request.user,
                election=election,
                defaults={'ip_address': get_client_ip(request)}
            )
            
            # Create vote
            Vote.objects.create(
                voter=request.user,
                candidate=candidate,
                ip_address=get_client_ip(request)
            )
            
            messages.success(
                request,
                f'Successfully voted for {candidate.name} as {candidate.position.get_name_display()}!'
            )
            
            # Redirect to election detail to continue voting
            return redirect('election_detail', election_id=election.id)
            
    except Exception as e:
        messages.error(request, f'Vote failed: {str(e)}')
        return redirect('enhanced_candidate_detail', candidate_id=candidate_id)


# Signal to update voter payment status
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Payment)
def update_voter_payment_status(sender, instance, **kwargs):
    """Automatically update voter's payment status when payment is successful"""
    if instance.status == 'success':
        try:
            voter_profile = instance.user.voter_profile
            voter_profile.has_paid_dues = True
            voter_profile.save()
        except VoterProfile.DoesNotExist:
            pass  # User hasn't registered as voter yet