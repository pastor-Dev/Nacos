from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
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
        return redirect('election_list')
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
                has_paid_dues=False,  # Will be updated by payment system
                is_verified=False  # Admin must verify
            )
            
            messages.success(
                request,
                'Registration submitted! An admin will verify your details shortly.'
            )
            return redirect('election_list')
            
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
        return redirect('election_list')
    
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
    
    return render(request, 'election_details.html', context)


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
            if value:  # Only add if a candidate was selected
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
        return redirect('election_details', election_id=election_id)
    
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
    
    return render(request, 'results.html', context)


@login_required
def candidate_detail(request, candidate_id):
    """Display candidate profile"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    context = {
        'candidate': candidate,
        'election': candidate.position.election,
    }
    
    return render(request, 'voting/candidate_detail.html', context)


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