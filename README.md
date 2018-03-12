# MorSchedule
iCalendar Generator for CQUPT  
生成 iCalendar 格式课表日历

## 依赖
	Python >= 3.5.2
	icalendar
	requests
	web.py==0.40-dev1
	pytz

## 配置

### 代理服务器

```python
proxies = {'http': 'http://127.0.0.1:8081'}
```

### 配置HTML课表地址

```python
resp = requests.get("http://xxx.xxx.xxx/.......")
```

*可以使内网外入服务部署外网*

## 直接运行

```
python MorSchedule.py
```

## Web访问

1. 在80端口开启服务  
```
python http.py 80
```  
2. 接口访问方式  
```
http://localhost/ics?xh=201xxxxxxx
```

## 异常处理
当前覆盖异常:

* 不能正确处理的时间格式  
* requests异常   

当Web服务出现异常情况时将会在课表名称/描述中添加'异常'前缀

##
Author: MorHop






