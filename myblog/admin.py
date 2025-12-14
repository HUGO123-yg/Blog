from django.contrib import admin
from .models import Blogpost, Classification, Tag, Comment, StoragePreference


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ['Comment_user', 'Comment_content', 'Comment_banned', 'Comment_status', 'Comment_time']
    readonly_fields = ['Comment_user', 'Comment_content', 'Comment_time']
    show_change_link = True


@admin.register(Blogpost)
class BlogpostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'Blog_status', 'is_pinned', 'classification', 'Vissible', 'created_at']
    list_filter = ['Blog_status', 'is_pinned', 'Vissible', 'classification', 'created_at']
    search_fields = ['title', 'slug', 'summary', 'Content']
    date_hierarchy = 'created_at'
    ordering = ['-is_pinned', '-created_at']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'views_count', 'likes_count']
    actions = ['publish', 'unpublish', 'pin', 'unpin', 'rebuild_slug']
    inlines = [CommentInline]

    def publish(self, request, queryset):
        queryset.update(Blog_status=1)
    publish.short_description = "批量发布"

    def unpublish(self, request, queryset):
        queryset.update(Blog_status=0)
    unpublish.short_description = "批量下线"

    def pin(self, request, queryset):
        queryset.update(is_pinned=True)
    pin.short_description = "批量置顶"

    def unpin(self, request, queryset):
        queryset.update(is_pinned=False)
    unpin.short_description = "批量取消置顶"

    def rebuild_slug(self, request, queryset):
        for post in queryset:
            post.slug = ''
            post.save(update_fields=['slug'])
    rebuild_slug.short_description = "重建 slug"


@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'item_count']
    search_fields = ['name']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'item_count']
    search_fields = ['name']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['Comment_id', 'Comment_time', 'Comment_user', 'Comment_blog', 'Comment_parent', 'Comment_banned', 'Comment_status']
    list_filter = ['Comment_banned', 'Comment_status', 'Comment_blog']
    search_fields = ['Comment_content']
    date_hierarchy = 'Comment_time'
    actions = ['ban_comments', 'unban_comments', 'approve_comments', 'retract_comments']

    def get_queryset(self, request):
        # Show all comments in admin, including banned ones
        base_qs = Comment.all_objects.get_queryset()
        return base_qs.select_related('Comment_user', 'Comment_blog').prefetch_related('replies')

    def ban_comments(self, request, queryset):
        queryset.update(Comment_banned=True)
    ban_comments.short_description = "批量封禁"

    def unban_comments(self, request, queryset):
        queryset.update(Comment_banned=False)
    unban_comments.short_description = "取消封禁"

    def approve_comments(self, request, queryset):
        queryset.update(Comment_status=1)
    approve_comments.short_description = "审核通过"

    def retract_comments(self, request, queryset):
        queryset.update(Comment_status=0)
    retract_comments.short_description = "撤回/草稿"


@admin.register(StoragePreference)
class StoragePreferenceAdmin(admin.ModelAdmin):
    list_display = ['use_object_storage', 'cdn_domain', 'updated_at']
    fields = ['use_object_storage', 'cdn_domain']
    readonly_fields = ['updated_at']

    def has_add_permission(self, request):
        if StoragePreference.objects.exists():
            return False
        return super().has_add_permission(request)
