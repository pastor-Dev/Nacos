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
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)