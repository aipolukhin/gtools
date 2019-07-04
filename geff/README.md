# geff
## Установка скрипта для пересчета проектов в программе g9

Проверено на Win7 SP1 RU-ru.
Имя активного пользователя должно быть на латинице, а также он должен обладать 
правами администратора.

! Установите программу [Micro-g LaCoste’s g Absolute Gravity Processing Software version g 9.0](http://microglacoste.com/product/micro-g-lacostes-g-absolute-gravity-processing-software/) с лицензионным ключом, если она не установлена.

! Убедитесь. что у компьютера имеется доступ в интернет.

1. Скачайте установочный файл [Miniconda2](https://repo.continuum.io/miniconda/Miniconda2-latest-Windows-x86_64.exe)
и запустите его с правами Администратора. 
- Checkbox "Install for: All Users (requires admin priveleges)"
- Checkbox "Add Anaconda to the system PATH..."

2. Запустите Anaconda Prompt с правами 
Администратора и выполните следующие команды:

```
conda install jupyter -y
    
conda install -c conda-forge zeep -y
    
conda install -c anaconda astropy -y
    
conda install -c synthicity prettytable -y
```

3. Установите [CobraWinLDTP-4.0.0](https://pypi.org/project/CobraWinLDTP/)

4. Для корректной работы пакета LDTP необходимо 
отключить UAC, либо выполнить следующие действия:
- Запустите cmd от имени администратора
- Поочередно выполнить в окне cmd следующие команды:

```
set LDTP_LISTEN_ALL_INTERFACE=1

netsh http add urlacl url=http://localhost:4118/ user=%USERNAME%

netsh http add urlacl url=http://+:4118/ user=%USERNAME%

netsh http add urlacl url=http://*:4118/ user=%USERNAME%
```

5. Запустить geff.reg

6. Скопируйте geff.py в папку C:\Program Files\Gtools

7. Перезагрузите компьютер
