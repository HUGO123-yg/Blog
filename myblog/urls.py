from rest_framework.routers import DefaultRouter
from .views import (
    BlogpostViewSet,
    CommentViewSet,
    ClassificationViewSet,
    TagViewSet,
)

router = DefaultRouter()
router.register(r'posts', BlogpostViewSet, basename='post')
router.register(r'comments', CommentViewSet, basename='comment')
router.register(r'classifications', ClassificationViewSet, basename='classification')
router.register(r'tags', TagViewSet, basename='tag')

urlpatterns = router.urls
