"""历史遗留：Flask 时代 Python 包的打包入口（非当前发行版本）。

`version` 是旧 Python 包 (`woniunote/`) 的版本号，与产品发行号无关。当前活跃实现是
C++ Drogon 后端 + Vue 3 前端，其发布版本以 `backend_cpp/CMakeLists.txt` 的
`project(... VERSION)` 为唯一来源，由 `scripts/check_release_version.sh` 校验
（迭代20 / Epic 20.5）。详见 README.md。
"""
from setuptools import setup, find_packages

# 定义扩展模块
extensions = [
    # 添加其他扩展模块
]

setup(
    name='woniunote',  # 项目的名称
    version='0.1.5',  # 旧 Python 包版本，非产品发行版本（见文件头说明）
    packages=find_packages(include=['woniunote', 'woniunote.*']),
    include_package_data=True,
    package_data={
        'woniunote': [
                    'configs/**/*',
                    'template/**/*',
                    'resource/**/*',
                    'common/**/*',
                    'controller/**/*',
                    'models/**/*',
                    'module/**/*',
                    'services/**/*']
    },
    author='cloudQuant',  # 作者名字
    author_email='yunjinqi@gmail.com',  # 作者邮箱
    description='A blog and website written by python, flask, html, css, javascript and mysql.',  # 项目描述
    long_description=open('README.md', encoding="utf-8").read(),  # 项目长描述（一般是 README 文件内容）
    long_description_content_type='text/markdown',  # 长描述的内容类型
    url='https://github.com/cloudQuant/woniunote',  # 项目的 URL
    install_requires=[
    ],  # 项目所需的依赖项列表
    ext_modules=extensions,  # 添加扩展模块
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        # 可以根据需要添加其他分类器
    ],  # 项目的分类器列表
)
