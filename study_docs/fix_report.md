## 修复概览
- 项目位于 `./myblog` 下的 Django 应用缺少必要路由文件，导致 `include('myblog.urls')` 时导入失败。
- 媒体文件相关设置缺失，`DEBUG=True` 时使用 `static()` 会触发 `ImproperlyConfigured: The 'MEDIA_URL' setting must not be empty`。
- 博文和评论的时间字段没有自动填充，会在创建记录时被要求手动提供时间。
- 自定义注册序列化器没有把扩展字段 `signature` 写回用户模型，导致注册时个性签名无法保存。
- 当前环境未安装 Django 依赖，运行 `python manage.py check` 报 `ModuleNotFoundError: No module named 'django'`，需在本地安装依赖后再验证。

## 变更细节
- 新增 `myblog/urls.py`，提供空的 `urlpatterns` 占位以满足路由导入。
- 在 `blog/settings.py` 增加 `MEDIA_URL` 和 `MEDIA_ROOT`，避免开发环境媒体路由配置报错。
- 将 `Blogpost.created_at` 与 `Comment.Comment_time` 改为 `auto_now_add=True`，创建记录时自动写入时间戳。
- 在 `myblog/serializers.py` 的 `CustomRegisterSerializer` 新增 `custom_signup`，注册流程中保存 `signature` 字段。

## 验证说明
- 运行 `python manage.py check` 前需要安装依赖：`pip install -r requirements`（或 `pip install -e .` 依据你的环境）。当前因本地未安装 Django 无法完成检查，安装后请重新执行校验。
