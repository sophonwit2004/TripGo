from django.contrib import admin
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Auth APIs
    path('api/register/', views.api_register, name='api_register'),
    path('api/login/', views.api_login, name='api_login'),
    path('api/logout/', views.api_logout, name='api_logout'),
    path('api/me/', views.api_me, name='api_me'),
    path('api/profile/update/', views.api_update_profile, name='api_update_profile'),
    
    # User Search & Social Relations APIs
    path('api/users/search/', views.api_users_search, name='api_users_search'),
    path('api/users/<int:user_id>/', views.api_user_detail, name='api_user_detail'),
    path('api/users/<int:user_id>/follow/', views.api_follow_toggle, name='api_follow_toggle'),
    
    # Post & Interaction APIs
    path('api/pins/', views.api_pins_list_create, name='api_pins_list_create'),
    path('api/pins/<int:pin_id>/like/', views.api_pin_like, name='api_pin_like'),
    path('api/pins/<int:pin_id>/comment/', views.api_pin_comment, name='api_pin_comment'),
    path('api/pins/<int:pin_id>/checkin/', views.api_pin_checkin, name='api_pin_checkin'),
    path('api/pins/<int:pin_id>/delete/', views.api_pin_delete, name='api_pin_delete'),

    # Stories & Notifications APIs
    path('api/stories/', views.api_stories, name='api_stories'),
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/read/', views.api_notifications_read, name='api_notifications_read'),

    # Serve image files located in BASE_DIR (temple.png, cafe.png, etc.)
    re_path(r'^(?P<path>.*\.(png|jpg|jpeg|gif|svg|webp|ico))$', serve, {'document_root': settings.BASE_DIR}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
