# 用官方 Python 镜像作为基础环境
FROM python:3.12-slim

# 设置容器里的工作目录，之后的命令都在这个目录下执行
WORKDIR /app

# 先只复制依赖文件并安装（这样改代码时不用每次重装依赖，利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 把项目所有代码复制进容器
COPY . .

# 容器启动时运行 Django 开发服务器，监听 0.0.0.0 让容器外能访问
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
