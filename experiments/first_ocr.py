import easyocr

reader = easyocr.Reader(['ne', 'en'], gpu=False)
results = reader.readtext('data/raw/kec_holiday_notice.jpg')

for bbox, text, conf in results:
    print(f"{conf:.2f}  {text}")