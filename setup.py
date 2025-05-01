from setuptools import setup, find_packages

# 定义扩展模块
extensions = [
    # 添加其他扩展模块
]

setup(
    name='woniunote',  # 项目的名称
    version='0.1.4',  # 版本号
    packages=find_packages(exclude=['demos', "docs", "tests", "scripts"]),
    package_data={
        'woniunote': [
                    'configs/**/*',
                    'template/**/*',
                    'resource/**/*']
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
