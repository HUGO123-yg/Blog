import hashlib
from pathlib import Path
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from . import object_storage
 

# Create your models here.
# class User(models.Model):
#     Userid = models.AutoField(primary_key=True,verbose_name='用户ID')
#     Username = models.CharField(max_length=32,verbose_name='用户名')
#     Password = models.CharField(max_length=255,verbose_name='密码')
#     Signature = models.TextField(default='',null=True,blank=True,verbose_name='个性签名')

class CustomUserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('邮箱必须填写'))
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('超级用户必须设置is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('超级用户必须设置is_superuser=True'))
        
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    """自定义用户模型"""
    Userid = models.AutoField(primary_key=True, verbose_name='用户ID')
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('必填。150个字符或更少。只能包含字母、数字和 @/./+/-/_ 字符。'),
        error_messages={
            'unique': _("该用户名已被使用。"),
        },
    )
    email = models.EmailField(_('email address'), unique=True)
    signature = models.TextField(default='', null=True, blank=True, verbose_name='个性签名')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    first_name = None
    last_name = None
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']
    
    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return self.username


def _get_year(value):
    if value:
        try:
            return value.year
        except AttributeError:
            pass
    return timezone.now().year


def cover_upload_to(instance, filename):
    """covers/{year}/{slug}/cover.<ext>"""
    slug_value = instance.slug or slugify(instance.title) or 'post'
    # Ensure slug is available for path generation
    instance.slug = slug_value
    year = _get_year(getattr(instance, 'created_at', None))
    ext = Path(filename).suffix.lstrip('.') or 'jpg'
    return f"covers/{year}/{slug_value}/cover.{ext}"


def post_image_upload_to(instance, filename):
    """images/{classification}/{year}/{slug}/<hash>.<ext>"""
    post = getattr(instance, 'post', None) or getattr(instance, 'blogpost', None)
    if not post:
        year = timezone.now().year
        slug_value = 'post'
    else:
        slug_value = post.slug or slugify(getattr(post, 'title', 'post')) or 'post'
        post.slug = slug_value
        year = _get_year(getattr(post, 'created_at', None))

    classification = getattr(getattr(post, 'classification', None), 'name', None) if post else None
    prefix = f"images/{classification}/" if classification else "images/"
    ext = Path(filename).suffix.lstrip('.') or 'jpg'
    digest = hashlib.md5(f"{filename}-{timezone.now().timestamp()}".encode()).hexdigest()  # nosec B303
    return f"{prefix}{year}/{slug_value}/{digest}.{ext}"


class Blogpost(models.Model):
    Blog_id = models.AutoField(primary_key=True, verbose_name='文章ID')
    title = models.CharField(max_length=200, unique=True, verbose_name='标题')
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='Slug')
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blogposts',
        verbose_name='作者'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='发布时间', db_index=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    Vissible = models.BooleanField(default=True, verbose_name='公开性')
    Content = models.TextField(blank=True, verbose_name ='文章内容')
    summary = models.TextField(blank=True, verbose_name='摘要')
    cover_image = models.ImageField(upload_to=cover_upload_to, null=True, blank=True, verbose_name='封面图')
    cover_object_url = models.URLField(max_length=1024, blank=True, default='', verbose_name='封面直链')
    views_count = models.PositiveIntegerField(default=0, verbose_name='浏览量')
    likes_count = models.PositiveIntegerField(default=0, verbose_name='点赞数')
    is_pinned = models.BooleanField(default=False, verbose_name='是否置顶')
    STATUS_CHOICES = [
        (0, '草稿'),
        (1, '已发布'), 
        (2, '已删除')
    ]
    Blog_status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name='文章状态', db_index=True)
    classification = models.ForeignKey(
        'Classification',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles',
        verbose_name='文章分类'
    ) 
    tags = models.ManyToManyField(
        'Tag',
        related_name='posts',
        blank=True,
        verbose_name='文章标签'
    )
    
    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title

    @property
    def cover_url(self):
        if self.cover_object_url:
            return self.cover_object_url
        return self.cover_image.url if self.cover_image else ''

    def _generate_unique_slug(self):
        base_slug = slugify(self.title) or 'post'
        slug_candidate = base_slug
        suffix = 1

        while Blogpost.objects.filter(slug=slug_candidate).exclude(pk=self.pk).exists():
            slug_candidate = f"{base_slug}-{suffix}"
            suffix += 1

        return slug_candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)
        self._sync_cover_object_storage()

    def _sync_cover_object_storage(self):
        if not self.cover_image or not object_storage.is_enabled():
            return
        if self.cover_object_url:
            return
        remote_url = object_storage.upload_field_file(self.cover_image)
        if remote_url:
            Blogpost.objects.filter(pk=self.pk).update(cover_object_url=remote_url)
            self.cover_object_url = remote_url


class PostImage(models.Model):
    """Markdown 正文图片存储，按分类/时间/slug 分层"""
    post = models.ForeignKey(
        Blogpost,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='文章'
    )
    image = models.ImageField(upload_to=post_image_upload_to, verbose_name='图片')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')
    object_storage_url = models.URLField(max_length=1024, blank=True, default='', verbose_name='对象存储直链')

    class Meta:
        verbose_name = '文章图片'
        verbose_name_plural = '文章图片'

    @property
    def url(self):
        if self.object_storage_url:
            return self.object_storage_url
        return self.image.url

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.image or not object_storage.is_enabled():
            return
        if self.object_storage_url:
            return
        remote_url = object_storage.upload_field_file(self.image)
        if remote_url:
            PostImage.objects.filter(pk=self.pk).update(object_storage_url=remote_url)
            self.object_storage_url = remote_url


class StoragePreference(models.Model):
    """Admin-toggle for using object storage; credentials remain in env."""
    use_object_storage = models.BooleanField(default=False, verbose_name='启用对象存储上传')
    cdn_domain = models.URLField(blank=True, default='', verbose_name='CDN 域名/直链前缀')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '存储偏好'
        verbose_name_plural = '存储偏好'

    def __str__(self):
        return '对象存储已启用' if self.use_object_storage else '使用本地存储'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'use_object_storage': False})
        return obj

class BaseTaxonomy(models.Model):
    """分类和标签的基类"""
    name = models.CharField(max_length=32, primary_key=True, verbose_name='名称')
    color = models.CharField(max_length=32, verbose_name='颜色')
    item_count_cache = models.PositiveIntegerField(default=0, editable=False, verbose_name='关联数量')

    @property
    def item_count(self):
        """缓存的关联项目数量"""
        return self.item_count_cache

    def refresh_item_count(self):
        """重新统计并缓存关联项目数量"""
        related_qs = getattr(self, self.count_relation_name)
        new_count = related_qs.count()
        if new_count != self.item_count_cache:
            self.item_count_cache = new_count
            self.save(update_fields=['item_count_cache'])
    
    class Meta:
        abstract = True

class Classification(BaseTaxonomy):
    """文章分类"""
    count_relation_name = 'articles'
    
    class Meta:
        verbose_name = '文章分类'
        verbose_name_plural = '文章分类'

class Tag(BaseTaxonomy):
    """文章标签"""
    count_relation_name = 'posts'
    
    class Meta:
        verbose_name = '文章标签'
        verbose_name_plural = '文章标签'

class CommentQuerySet(models.QuerySet):
    def with_replies(self):
        """Prefetch replies to avoid N+1 on nested comment rendering."""
        return self.prefetch_related('replies')

    def visible(self):
        """Public comments (exclude banned)."""
        return self.filter(Comment_banned=False)


class CommentManager(models.Manager.from_queryset(CommentQuerySet)):
    def get_queryset(self):
        # Default to visible comments only for public queries
        return super().get_queryset().filter(Comment_banned=False)


class Comment(models.Model):
    Comment_id = models.AutoField(primary_key=True,verbose_name='评论ID')
    Comment_time = models.DateTimeField(auto_now_add=True, verbose_name='评论时间', db_index=True)
    Comment_content = models.TextField(blank=True, verbose_name ='评论内容')
    STATUS_CHOICES = [
        (0, '草稿'),
        (1, '已发布'), 
        (2, '已删除')
    ]
    Comment_status = models.IntegerField(choices=STATUS_CHOICES, default=0, verbose_name='评论状态')
    Comment_banned = models.BooleanField(default=False, verbose_name='是否封禁')
    Comment_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='comments',
        verbose_name='评论用户'
    )
    Comment_blog = models.ForeignKey(
        Blogpost, 
        on_delete=models.CASCADE, 
        null=False,
        blank=False,
        related_name='comments',
        verbose_name='评论文章',
        db_index=True
    )
    Comment_parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='上级评论',
        db_index=True
    )
    objects = CommentManager()
    all_objects = CommentQuerySet.as_manager()
    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['-Comment_time']  # 按评论时间倒序排列

    def __str__(self):
        return f"评论{self.Comment_id}"

    def clean(self):
        """Ensure child comments reference the same article as their parent."""
        super().clean()
        if self.Comment_parent and self.Comment_parent.Comment_blog_id != self.Comment_blog_id:
            raise ValidationError(_('子评论与父评论必须属于同一文章'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)



@receiver(post_save, sender=Blogpost)
def update_classification_on_save(sender, instance, created, **kwargs):
    """
    保存后处理分类计数相关逻辑
    """
    old_classification = getattr(instance, '_old_classification', None)
    new_classification = instance.classification
    if old_classification == new_classification:
        return

    for classification in (old_classification, new_classification):
        if classification:
            classification.refresh_item_count()

@receiver(post_delete, sender=Blogpost)
def update_classification_on_delete(sender, instance, **kwargs):
    """
    删除后处理分类计数相关逻辑
    """
    if instance.classification:
        instance.classification.refresh_item_count()

@receiver(m2m_changed, sender=Blogpost.tags.through)
def update_tag_on_change(sender, instance, action, **kwargs):
    """
    标签变更时处理计数相关逻辑
    """
    if action == "pre_clear":
        # 在清空前记录旧标签以便刷新计数
        instance._old_tags = set(instance.tags.values_list('pk', flat=True))
        return

    tags_to_refresh = set()
    if action in {"post_add", "post_remove"}:
        pk_set = kwargs.get("pk_set") or set()
        tags_to_refresh.update(pk_set)
        tags_to_refresh.update(instance.tags.values_list('pk', flat=True))
    elif action == "post_clear":
        tags_to_refresh.update(getattr(instance, "_old_tags", set()))
        instance._old_tags = set()
    else:
        return

    if not tags_to_refresh:
        return

    for tag in Tag.objects.filter(pk__in=tags_to_refresh):
        tag.refresh_item_count()

# 在保存前记录旧的分类，用于判断分类是否变化
@receiver(pre_save, sender=Blogpost)
def remember_old_classification(sender, instance, **kwargs):
    """
    在保存前记录文章原来的分类
    """
    if instance.pk:
        try:
            old_instance = Blogpost.objects.get(pk=instance.pk)
            instance._old_classification = old_instance.classification
        except Blogpost.DoesNotExist:
            instance._old_classification = None
    else:
        instance._old_classification = None
