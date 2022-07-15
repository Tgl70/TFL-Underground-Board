import os
import sys
import math
import json
import time
import requests
from pytz import timezone
from datetime import datetime
from helper import get_device
from PIL import ImageFont, Image
from luma.core.render import canvas


def loadConfig():
    with open('config.json', 'r') as jsonConfig:
        data = json.load(jsonConfig)
        return data


def makeFont(name, size):
    font_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            'fonts',
            name
        )
    )
    return ImageFont.truetype(font_path, size)


def generateBoard(device, data, station):
    with canvas(device) as display:
        if not data:
            welcome_msg = "Welcome to " + station['name'].replace('Underground Station', '')
            w1, h1 = display.textsize(welcome_msg, font_regular)
            display.text((((displayWidth-w1)/2), 0), text=welcome_msg, font=font_regular, fill="orange")
        else:
            row_num = 1
            for train in data:
                
                # Display the number and the destination
                display.text((0, ((row_num-1) * 14)), text=str(row_num), font=font_regular, fill="orange")
                display.text((10, ((row_num-1) * 14)), text=train['destination'], font=font_regular, fill="orange")

                # Display the time left to arrive
                w_time, h_time = display.textsize(train['timeLeft'], font_regular)
                display.text((displayWidth-(w_time), ((row_num-1) * 14)), text=train['timeLeft'], font=font_regular, fill="orange")
                row_num += 1

            # Indicates that the train is approaching if arrival is within 15 seconds.
            if data[0]['timeLeftSeconds'] < 15:
                w1, h1 = display.textsize('*** STAND BACK - TRAIN APPROACHING ***', font_regular)
                display.text((((displayWidth-w1)/2), ((3) * 14)), text='*** STAND BACK - TRAIN APPROACHING ***', font=font_regular, fill="orange")

        # Generate clock at the bottom
        current_time_in_london = datetime.now(timezone('Europe/London'))
        current_time_milliseconds = int(str(round(time.time() * 1000))[-3:])
        if current_time_milliseconds > 500:
            current_time = current_time_in_london.strftime("%H:%M:%S")
        else:
            current_time = current_time_in_london.strftime("%H %M %S")
        w1, h1 = display.textsize(current_time, font_bold)
        display.text((((displayWidth-w1)/2), (displayHeight-h1)), text=current_time, font=font_bold, fill="orange")


def queryTFL(config):
    response = requests.get(config['query'])
    response_json = json.loads(response.text)

    station = {
        'id': response_json[0]['naptanId'],
        'name': response_json[0]['stationName'],
    }

    data = []
    for r in response_json:
        if config['platform'] in r['platformName']:
            timeToStation = r['timeToStation']
            if timeToStation >= 60:
                # Round up to the next minute
                arrival_time = str(math.ceil(timeToStation/60))
                arrival_text = ' mins'
            elif timeToStation < 60 and timeToStation > 30:
                # Round up to 1 minute 
                arrival_time = str(math.ceil(timeToStation/60))
                arrival_text = ' min'
            else:
                # Due
                arrival_time = ''
                arrival_text = 'Due'
            train = {
                'line': r['lineName'],
                'destination': r['towards'],
                'platform': r['platformName'],
                'timeLeftSeconds': r['timeToStation'],
                'timeLeft': arrival_time + arrival_text,
            }
            data.append(train)
    data = sorted(data, key = lambda i: i['timeLeftSeconds'])
    data = data[:3]

    return data, station


if __name__ == '__main__':
    try:
        config = loadConfig()
        device = get_device()
        font_regular = makeFont('London Underground Regular.ttf', 9)
        font_bold = makeFont('London Underground Bold.ttf', 9)
        displayWidth = config['displayWidth']
        displayHeight = config['displayHeight']

        data, station = queryTFL(config)
        generateBoard(device, data, station)

        last_refresh_time = time.time() 

        while True:
            if(time.time() - last_refresh_time >= config["refreshTime"]):
                data, station = queryTFL(config)
                last_refresh_time = time.time()

            generateBoard(device, data, station)
            time.sleep(.1)

        
    except KeyboardInterrupt:
        pass
    except ValueError as e:
        print(e)
    except Exception as e:
        raise e
