# MorScheduleiCalendar Generator for CQUPT  生成iCalendar格式课表日历## 依赖	Python <= 2.7	iCalendar(pypi) <=3.9	requests(pypi)	web.py## 配置### 代理服务器```pythonproxies = {'http': 'http://127.0.0.1:8081'}```### 可以使内网外入服务部署外网## 直接运行```python MorSchedule.py```## Web访问在80端口开启服务  ```python http.py 80```  接口访问方式  ```http://localhost/ics?xh=201xxxxxxx```##Author: MorHop