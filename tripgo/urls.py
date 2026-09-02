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
    
    # Pin & Interaction APIs
    path('api/pins/', views.api_pins_list_create, name='api_pins_list_create'),
    path('api/pins/<int:pin_id>/like/', views.api_pin_like, name='api_pin_like'),
    path('api/pins/<int:pin_id>/comment/', views.api_pin_comment, name='api_pin_comment'),
    path('api/pins/<int:pin_id>/checkin/', views.api_pin_checkin, name='api_pin_checkin'),
    path('api/pins/<int:pin_id>/delete/', views.api_pin_delete, name='api_pin_delete'),

    # Serve image files located in BASE_DIR (temple.png, cafe.png, etc.)
    re_path(r'^(?P<path>.*\.(png|jpg|jpeg|gif|svg|webp|ico))$', serve, {'document_root': settings.BASE_DIR}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
