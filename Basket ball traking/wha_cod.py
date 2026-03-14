import pywhatkit as pwt
import time
# import pyautogui
name = ['Umang ']

num_list = [ '+917016968849']

# print(len(num_list)-1)
index = 0
str1=("\nThis message from whatsapp bot!!\n"+

"\nDesigned by ssasit student\n"+

"\nHave a great day !!\n"
)
for x in num_list:
    strr = "Hello "+name[index] + str1
    # print(strr)
    pwt.sendwhatmsg_instantly(x, strr)
    index = index+1
    time.sleep(0.5)