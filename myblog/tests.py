from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import Blogpost, Comment

User = get_user_model()

class BlogpostModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user_blog', email='user_blog@example.com', password='pass')

    def test_auto_slug_generation_and_uniqueness(self):
        first = Blogpost.objects.create(
            title='Hello World!',
            slug='',
            author=self.user,
            Content='内容',
            Vissible=True,
            Blog_status=1
        )
        self.assertEqual(first.slug, slugify('Hello World!'))

        second = Blogpost.objects.create(
            title='Hello World!!',
            slug='',
            author=self.user,
            Content='内容2',
            Vissible=True,
            Blog_status=1
        )
        self.assertTrue(second.slug.startswith(slugify('Hello World!')))
        self.assertNotEqual(second.slug, first.slug)


class CommentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='pass')
        self.post = Blogpost.objects.create(
            title='测试文章',
            slug='test-post',
            author=self.user,
            Content='测试文章',
            Vissible=True,
            Blog_status=1
        )

    def test_nested_comments(self):
        root = Comment.objects.create(Comment_user=self.user, Comment_blog=self.post, Comment_content='根评论')
        child1 = Comment.objects.create(Comment_user=self.user, Comment_blog=self.post, Comment_parent=root, Comment_content='子评论1')
        child2 = Comment.objects.create(Comment_user=self.user, Comment_blog=self.post, Comment_parent=root, Comment_content='子评论2')
        grandchild = Comment.objects.create(Comment_user=self.user, Comment_blog=self.post, Comment_parent=child1, Comment_content='孙评论')

        self.assertEqual(root.replies.count(), 2)
        self.assertIn(child1, root.replies.all())
        self.assertIn(child2, root.replies.all())
        self.assertEqual(child1.replies.count(), 1)
        self.assertIn(grandchild, child1.replies.all())

    def test_ban_flag(self):
        c = Comment.objects.create(Comment_user=self.user, Comment_blog=self.post, Comment_content='可封禁评论')
        self.assertFalse(c.Comment_banned)
        c.Comment_banned = True
        c.save(update_fields=['Comment_banned'])
        with self.assertRaises(Comment.DoesNotExist):
            Comment.objects.get(pk=c.pk)
        c_db = Comment.all_objects.get(pk=c.pk)
        self.assertTrue(c_db.Comment_banned)

    def test_child_comment_must_match_parent_post(self):
        other_post = Blogpost.objects.create(
            title='其他文章',
            slug='other-post',
            author=self.user,
            Content='其他内容',
            Vissible=True,
            Blog_status=1
        )
        parent = Comment.objects.create(
            Comment_user=self.user,
            Comment_blog=self.post,
            Comment_content='父评论'
        )
        with self.assertRaises(ValidationError) as cm:
            Comment.objects.create(
                Comment_user=self.user,
                Comment_blog=other_post,
                Comment_parent=parent,
                Comment_content='跨文章子评论'
            )
        self.assertIn('子评论与父评论必须属于同一文章', cm.exception.messages)

    def test_default_manager_excludes_banned_comments(self):
        Comment.objects.create(Comment_user=self.user, Comment_blog=self.post, Comment_content='可见评论')
        Comment.all_objects.create(
            Comment_user=self.user,
            Comment_blog=self.post,
            Comment_content='被封禁',
            Comment_banned=True
        )
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(Comment.objects.visible().count(), 1)
        self.assertEqual(Comment.all_objects.count(), 2)
