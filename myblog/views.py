from django.utils.dateparse import parse_datetime
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly, BasePermission, SAFE_METHODS
from rest_framework.response import Response

from .models import Blogpost, Comment, Classification, Tag
from .serializers import BlogpostSerializer, CommentSerializer, ClassificationSerializer, TagSerializer


class IsAuthorOrAdminOrReadOnly(BasePermission):
    """
    Allow safe methods for everyone; write actions only for author or admins.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_staff or user.is_superuser or getattr(obj, 'author', None) == user


class BlogpostViewSet(viewsets.ModelViewSet):
    serializer_class = BlogpostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrAdminOrReadOnly]
    lookup_field = 'slug'

    def get_queryset(self):
        qs = Blogpost.objects.select_related('author', 'classification').prefetch_related('tags')
        params = self.request.query_params

        classification_param = params.get('classification')
        if classification_param:
            values = classification_param.split(',') if ',' in classification_param else [classification_param]
            names = [v for v in values if not v.isdigit()]
            ids = [v for v in values if v.isdigit()]
            q_obj = models.Q()
            if names:
                q_obj |= models.Q(classification__name__in=names) | models.Q(classification_id__in=names)
            if ids:
                q_obj |= models.Q(classification_id__in=ids)
            qs = qs.filter(q_obj)

        tags_param = params.getlist('tags') or params.get('tags')
        if tags_param:
            if not isinstance(tags_param, list):
                tags_param = [v for v in tags_param.split(',') if v]
            tag_filters = []
            for tag in tags_param:
                if str(tag).isdigit():
                    tag_filters.append(int(tag))
                else:
                    tag_filters.append(tag)
            qs = qs.filter(models.Q(tags__pk__in=[v for v in tag_filters if isinstance(v, int)]) | models.Q(tags__name__in=[v for v in tag_filters if isinstance(v, str)])).distinct()

        status_param = params.get('status') or params.get('Blog_status')
        if status_param is not None:
            qs = qs.filter(Blog_status=status_param)

        is_pinned = params.get('is_pinned')
        if is_pinned is not None:
            if is_pinned.lower() in {'true', '1'}:
                qs = qs.filter(is_pinned=True)
            elif is_pinned.lower() in {'false', '0'}:
                qs = qs.filter(is_pinned=False)

        start = parse_datetime(params.get('start')) if params.get('start') else None
        end = parse_datetime(params.get('end')) if params.get('end') else None
        if start:
            qs = qs.filter(created_at__gte=start)
        if end:
            qs = qs.filter(created_at__lte=end)

        allowed_ordering = {'created_at', '-created_at', 'is_pinned', '-is_pinned', 'Blog_status', '-Blog_status'}
        ordering = params.get('ordering')
        if ordering in allowed_ordering:
            qs = qs.order_by(ordering)

        return qs

    def get_object(self):
        lookup_value = self.kwargs.get(self.lookup_field)
        qs = self.get_queryset()
        if lookup_value and str(lookup_value).isdigit():
            obj = get_object_or_404(qs, pk=lookup_value)
        else:
            obj = get_object_or_404(qs, slug=lookup_value)

        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        serializer.save(author=self.request.user if self.request.user.is_authenticated else None)

    @action(detail=True, methods=['get', 'post'], url_path='comments', permission_classes=[IsAuthenticatedOrReadOnly])
    def comments(self, request, **kwargs):
        post = self.get_object()
        if request.method.lower() == 'get':
            max_depth = request.query_params.get('depth')
            try:
                max_depth_val = int(max_depth) if max_depth is not None else 2
            except ValueError:
                max_depth_val = 2
            comments_qs = Comment.objects.with_replies().filter(Comment_blog=post, Comment_parent__isnull=True)
            serializer = CommentSerializer(
                comments_qs,
                many=True,
                context={
                    'request': request,
                    'max_depth': max_depth_val,
                    'current_depth': 1,
                }
            )
            return Response(serializer.data)

        serializer = CommentSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save(Comment_blog=post)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    queryset = Comment.objects.with_replies().select_related('Comment_user', 'Comment_blog', 'Comment_parent')
    http_method_names = ['get', 'post', 'patch', 'put', 'delete']

    def get_queryset(self):
        qs = super().get_queryset()
        post_id = self.request.query_params.get('post')
        if post_id:
            qs = qs.filter(Comment_blog=post_id)
        parent_id = self.request.query_params.get('parent')
        if parent_id:
            qs = qs.filter(Comment_parent=parent_id)
        return qs


class ClassificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClassificationSerializer
    queryset = Classification.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TagSerializer
    queryset = Tag.objects.all()
    permission_classes = [IsAuthenticatedOrReadOnly]
