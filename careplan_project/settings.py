"""
Django 配置文件（精简版）。
注意：我们故意不配置数据库，因为今天数据存在内存里。
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# 开发用的密钥，生产环境绝不能这样硬编码（后面会讲怎么用环境变量管理）
SECRET_KEY = "dev-only-not-secret-change-me"

# 开发模式：出错时显示详细报错。生产环境必须设为 False
DEBUG = True

# 允许哪些域名访问，开发阶段用 * 全放开
ALLOWED_HOSTS = ["*"]

# 注册我们用到的 Django app
INSTALLED_APPS = [
    "django.contrib.contenttypes",  # ← 加：ORM 基础，migrate 需要
    "django.contrib.auth",          # ← 加：很多东西依赖它
    "django.contrib.staticfiles",
    "orders",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    # 注意：我们去掉了 CSRF 中间件，因为今天前端用最简单的 fetch，
    # 不想引入 CSRF token 的复杂度。生产环境必须开启 CSRF 保护！
]

ROOT_URLCONF = "careplan_project.urls"

# 模板引擎配置，告诉 Django 去 app 的 templates 目录找 HTML
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "DIRS": [],
        "OPTIONS": {"context_processors": []},
    },
]

WSGI_APPLICATION = "careplan_project.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST"),     # "db" → compose 里的服务名
        "PORT": os.environ.get("POSTGRES_PORT"),
    }
}

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
