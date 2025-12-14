from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.html import escape
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from .models import Blogpost, Comment, Classification, Tag

try:
    import markdown as md
except ImportError:  # pragma: no cover - optional dependency
    md = None

try:
    import bleach
except ImportError:  # pragma: no cover - optional dependency
    bleach = None

SAFE_HTML_TAGS = [
    'p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'img'
]
SAFE_HTML_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title', 'name', 'rel'],
    'img': ['src', 'alt', 'title'],
}
SAFE_PROTOCOLS = ['http', 'https', 'data']


def render_markdown_safe(content: str) -> str:
    """
    Render markdown text to sanitized HTML. If markdown/bleach are unavailable,
    fall back to escaped text with simple line breaks.
    """
    if not content:
        return ''

    if md:
        html = md.markdown(
            content,
            extensions=['extra', 'codehilite', 'nl2br']
        )
    else:
        escaped = escape(content).replace("\n", "<br>")
        html = f"<p>{escaped}</p>"

    if bleach:
        html = bleach.clean(
            html,
            tags=SAFE_HTML_TAGS,
            attributes=SAFE_HTML_ATTRIBUTES,
            protocols=SAFE_PROTOCOLS,
            strip=True
        )
        # Ensure external links have rel to mitigate tabnabbing
        html = html.replace('<a ', '<a rel="noopener" ')
    return html

User = get_user_model()

class CustomRegisterSerializer(RegisterSerializer):
    """自定义注册序列化器"""
    signature = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('username', ''),
            'password1': self.validated_data.get('password1', ''),
            'email': self.validated_data.get('email', ''),
            'signature': self.validated_data.get('signature', ''),
        }
    
    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        return user

    def custom_signup(self, request, user):
        """注册时把扩展字段写入用户模型"""
        user.signature = self.cleaned_data.get('signature', '')
        user.save(update_fields=['signature'])

class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    class Meta:
        model = User
        fields = ('Userid', 'username', 'email', 'signature', 'avatar', 'created_at', 'updated_at')
        read_only_fields = ('Userid', 'created_at', 'updated_at')


class ClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classification
        fields = ['name', 'color', 'item_count_cache']
        read_only_fields = ['item_count_cache']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['name', 'color', 'item_count_cache']
        read_only_fields = ['item_count_cache']


class CommentSerializer(serializers.ModelSerializer):
    Comment_user = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'Comment_id',
            'Comment_time',
            'Comment_content',
            'Comment_status',
            'Comment_banned',
            'Comment_user',
            'Comment_blog',
            'Comment_parent',
            'replies',
        ]
        # Comment_banned managed server-side; keep read-only for public API
        read_only_fields = [
            'Comment_id',
            'Comment_time',
            'Comment_banned',
            'Comment_status',
            'Comment_user',
            'replies',
        ]

    def get_replies(self, obj):
        max_depth = self.context.get('max_depth', 2)
        current_depth = self.context.get('current_depth', 1)
        if current_depth >= max_depth:
            return []
        children = obj.replies.all()
        return CommentSerializer(
            children,
            many=True,
            context={**self.context, 'current_depth': current_depth + 1}
        ).data

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['Comment_user'] = request.user
        return super().create(validated_data)


class BlogpostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    classification = ClassificationSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    classification_id = serializers.PrimaryKeyRelatedField(
        queryset=Classification.objects.all(),
        source='classification',
        allow_null=True,
        required=False,
        write_only=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False,
        write_only=True
    )
    content_html = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Blogpost
        fields = [
            'Blog_id',
            'title',
            'slug',
            'author',
            'classification',
            'classification_id',
            'tags',
            'tag_ids',
            'created_at',
            'updated_at',
            'Vissible',
            'Content',
            'content_html',
            'summary',
            'cover_image',
            'views_count',
            'likes_count',
            'is_pinned',
            'Blog_status',
        ]
        read_only_fields = [
            'Blog_id',
            'slug',
            'author',
            'created_at',
            'updated_at',
            'views_count',
            'likes_count',
        ]

    def create(self, validated_data):
        request = self.context.get('request')
        tags = validated_data.pop('tag_ids', [])
        classification = validated_data.pop('classification', None)
        if request and request.user.is_authenticated:
            validated_data['author'] = request.user
        if classification:
            validated_data['classification'] = classification
        instance = super().create(validated_data)
        if tags:
            instance.tags.set(tags)
        return instance

    def update(self, instance, validated_data):
        # Prevent slug overwrite through serializer; model handles generation
        validated_data.pop('slug', None)
        tags = validated_data.pop('tag_ids', None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        return instance

    def get_content_html(self, obj):
        return render_markdown_safe(obj.Content or '')
