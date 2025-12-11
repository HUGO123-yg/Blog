from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser,BaseUserManager
from django.utils.translation import gettext_lazy as _
from rest_framework.relations import PrimaryKeyRelatedField

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
        return self.usernameCharField(max_length=32,verbose_name='用户名')
    Password = models.CharField(max_length=255,verbose_name='密码')
    Signature = models.TextField(default='',blank=True,verbose_name='个性签名')

class Blogpost(models.Model):
    Blog_id = models.AutoField(primary_key=True, verbose_name='文章ID')
    Creat_at= models.DateTimeField(verbose_name='发布时间')
    Vissible = models.BooleanField(default=True, verbose_name='公开性')
    Content = models.TextField(blank=True, verbose_name ='文章内容')
    STATUS_CHOICES = [
        (0, '草稿'),
        (1, '已发布'), 
        (2, '已删除')
    ]
    Blog_status = models.IntegerField(choices=STATUS_CHOICES, default=0,verbose_name='文章状态')
    classification = models.ForeignKey(
        'Class_ification', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='articles',  # 重要：定义反向关系名称
        verbose_name='文章分类'
    )
    
    class Meta:
        verbose_name = '文章'
        verbose_name_plural = '文章'
        ordering = ['-Posttimee']  # 按发布时间倒序排列

    def __str__(self):
        return f"文章{self.Blog_id}"

class BaseTaxonomy(models.Model):
    """分类和标签的基类"""
    name = models.CharField(max_length=32, primary_key=True, verbose_name='名称')
    color = models.CharField(max_length=32, verbose_name='颜色')
    
    @property
    def item_count(self):
        """自动计算关联项目数量"""
        # 子类需要实现 articles 或 posts 等相关名称
        return getattr(self, self.count_relation_name).count()
    
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

class Comment(models.Model):
    Comment_id = models.AutoField(PrimaryKey=True,verbose_name='评论ID')
    Comment_time = models.DateTimeField(verbose_name='评论时间')
    Comment_content = models.TextField(blank=True, verbose_name ='评论内容')
    Comment_status = models.IntegerField(choices=STATUS_CHOICES, default=0,verbose_name='评论状态')
    Comment_user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='comments',  # 重要：定义反向关系名称
        verbose_name='评论用户'
    )
    Comment_blog = models.ForeignKey(
        Blogpost, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='comments',  # 重要：定义反向关系名称
        verbose_name='评论文章'
    )
    class Meta:
        verbose_name = '评论'
        verbose_name_plural = '评论'
        ordering = ['-Comment_time']  # 按评论时间倒序排列

    def __str__(self):
        return f"评论{self.Comment_id}"



# 信号处理器 - 当文章保存或删除时自动处理
@receiver(post_save, sender=Blogpost)
@receiver(post_delete, sender=Blogpost)
def update_classification_count(sender, instance, **kwargs):
    """
    当文章被创建、更新或删除时，更新相关分类的文章计数缓存
    这里可以添加缓存更新逻辑
    """
    pass

# 在保存前记录旧的分类，用于判断分类是否变化
@receiver(post_save, sender=Blogpost)
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