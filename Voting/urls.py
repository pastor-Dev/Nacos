from django.urls import path
from . import views


urlpatterns = [
    # Election pages
    path('elections/', views.election_List, name='election_list'),
    path('elections/<int:election_id>/', views.election_detail, name='election_details'),
    path('elections/<int:election_id>/results/', views.election_results, name='results'),
    
    # Voting
    path('elections/<int:election_id>/vote/', views.cast_vote, name='cast_vote'),
    
    # Voter registration
    path('voter/register/', views.voter_registration, name='voter_registration'),
    
    # Candidate details
    path('candidate/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidate/<int:candidate_id>/profile/', views.enhanced_candidate_detail, name='enhanced_candidate_detail'),
    path('elections/<int:election_id>/candidates/', views.meet_candidates, name='meet_candidates'),
    path('elections/<int:election_id>/compare/', views.compare_candidates, name='compare_candidates'),
    path('candidate/<int:candidate_id>/vote/', views.vote_for_candidate, name='vote_for_candidate'),
]