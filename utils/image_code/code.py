from PIL import Image, ImageDraw, ImageFont

def verify_code():
    #引入随机函数模块
    import random,os
    #定义变量，用于画面的背景色、宽、高
    bgcolor = (random.randrange(20, 100), random.randrange(
        20, 100), 255)
    width = 90
    height = 41
    #创建画面对象
    im = Image.new('RGB', (width, height), bgcolor)
    #创建画笔对象
    draw = ImageDraw.Draw(im)
    #调用画笔的point()函数绘制噪点
    for i in range(0, 100):
        xy = (random.randrange(0, width), random.randrange(0, height))
        fill = (random.randrange(0, 255), 255, random.randrange(0, 255))
        draw.point(xy, fill=fill)
    #定义验证码的备选值
    str1 = 'ABCD123EFGHIJK456LMNOPQRS789TUVWXYZ0'
    #随机选取4个值作为验证码
    rand_str = ''
    #构造字体对象，ubuntu的字体路径为“/usr/share/fonts/truetype/freefont”
    font = ImageFont.load_default()
    # font = ImageFont.load("FontAwesome.otf")
    font = ImageFont.truetype(r"C:\Users\CY-1.DESKTOP-UAN7HVD\Downloads\PublicSans\Public Sans\PublicSans-Regular.otf", 23)
    #构造字体颜色

    fontcolor = (255, random.randrange(0, 255), random.randrange(0, 255))
    for i in range(0, 4):
        rand_str += str1[random.randrange(0, len(str1))]
    draw.text((5, 2), rand_str[0], font=font, fill=fontcolor)
    draw.text((25, 2), rand_str[1], font=font, fill=fontcolor)
    draw.text((50, 2), rand_str[2], font=font, fill=fontcolor)
    draw.text((75, 2), rand_str[3], font=font, fill=fontcolor)


    #释放画笔
    del draw
    import io
    byteIo = io.BytesIO()
    im.save(byteIo, 'png')
    return "".join(random.sample(str1+"12345",24)),rand_str, byteIo.getvalue()