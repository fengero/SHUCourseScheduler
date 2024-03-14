# 简介

这是一个简单的实用工具，能够获取教务系统的课表信息生成ics日历文件。

可将将此文件导入到手机/电脑/平板的日历软件和第三方课表app中。

# 开始使用

## 1.傻瓜式

你可以获取releases中已经打包好的exe文件，下载到电脑上双击运行

## 2.源代码安装

### 前提

确保你的系统已经安装了Python 3.x。你可以通过在终端运行`python --version`来检查Python版本。

### 使用

1. 下载 `SHUCourseScheduler.py`

2. 使用`pip install requests rsa icalendar lxml pytz` 安装项目所需依赖

3. 使用 `python SHUCourseScheduler.py`  启动程序

	程序会在程序运行目录下生成ics文件
