import speech_recognition as sr

from gtts import gTTS
import os
import time
import datetime

import sys

from subprocess import call
import subprocess

import re
from spellchecker import SpellChecker

import pymssql

import pandas as pd

# Define the SQL Server connection parameters
SERVER = '192.168.1.16'
DATABASE = 'VoiceOrder'
USERNAME = 'amit'
PASSWORD = 'amit123'

conn = pymssql.connect(host=SERVER, user=USERNAME, password=PASSWORD, database=DATABASE)
cursor = conn.cursor()

# Initialize the spell checker
spell = SpellChecker()


# Initialize the recognizer
recognizer = sr.Recognizer()

# Add custom corrections for common mistakes
custom_corrections = {
    'cork': 'coke',
    'cock': 'coke',
    'phone': 'one',
    'man': 'one',
    'brother': 'burger',
    'shake': 'shakes',
    'pepsi': 'pepsi',
    'peps': 'pepsi',
    'to': 'two',
    'tu': 'two',
    'shacks': 'shakes',
    'for':'four'
}

# Define the food menu with prices
food_menu = {
    "pepsi": 20,
    "burger": 50,
    "pizza": 100,
    "coke": 20,
    "shakes": 70
}

def correct_spelling(word):
    # Correct custom common mistakes first
    if word in custom_corrections:
        return custom_corrections[word]
    # Use the spell checker for other words
    corrected = spell.correction(word)
    return corrected

def parse_order_text(text, menu):
    # Normalize the text
    text = text.lower()
    
    # Predefined words for numbers
    number_words = {
        'zero': 0,
        'one': 1,
        'two': 2,
        'three': 3,
        'four': 4,
        'five': 5,
        'six': 6,
        'seven': 7,
        'eight': 8,
        'nine': 9,
        'ten': 10,
        'eleven':11,
        'fifteen':15,
        'twenty':20
    }
    
    # Function to convert number words to digits
    def word_to_num(word):
        return number_words.get(word, 1)
    
    # Tokenize the text into quantity-item pairs
    tokens = text.split()
    print(tokens)
    
    # Dictionary to store the final order
    
    order = {}
    total_cost = 0
    
    i = 0
    while i < len(tokens):
        # Get the quantity
        quantity_str = tokens[i]
        if quantity_str.isdigit():
            quantity = int(quantity_str)
        else:
            print("corrected string before corrected: ", quantity_str)
            quantity_str = correct_spelling(quantity_str)
            print("corrected string before corrected: ", quantity_str)
            quantity = word_to_num(quantity_str)
        
        # Get the item(s) (can be multiple words)
        item = []
        i += 1
        while i < len(tokens) and not tokens[i].isdigit() and tokens[i] not in number_words:
            corrected_token = correct_spelling(tokens[i])
            item.append(corrected_token)
            i += 1
        
        item_name = ' '.join(item)
        
        if item_name in order:
            order[item_name] += quantity
        else:
            order[item_name] = quantity
        
        # Calculate the cost
        if item_name in menu:
            total_cost += menu[item_name] * quantity
        else:
            print(f"Warning: {item_name} not found in the menu.")
            
        # Get the current date and time
        current_datetime = datetime.datetime.now()

        # Display the current date and time
        print(current_datetime)
    
    return order, total_cost, current_datetime

def play(path):
    subprocess.Popen(['mpg123','-q', path]).wait()

def robot(text):
    
    obj = gTTS(text = text, slow = False, lang = 'en')
    filename = "Neworder.mp3"
    obj.save(filename)
    play('/home/pi/speech_chatbot/'+filename)
    #print(text)
    
def recognize_speech(text):
    # Use the default microphone as the audio source
    with sr.Microphone() as source:
        print(text)
        # Adjust for ambient noise
        recognizer.adjust_for_ambient_noise(source)
        # Listen for speech input
        
        audio = recognizer.listen(source)
        time.sleep(3)

        try:
            # Convert speech to text using Google Web Speech API
            text = recognizer.recognize_google(audio)
            return text
        
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print("Error: Could not request results from Google Speech Recognition service; {0}".format(e))

while True:
    try:
        text = 'Speak to Give Order '
        print(food_menu)
        # speak the above line
        robot(text)
        
        order = recognize_speech(text)

        print("********************************************************")
        text2 = "Your order is: " + order
        print(text2)
        print("********************************************************")
        robot(text2)
        
        order, total_cost, date_time = parse_order_text(order, food_menu)
        print(order)
        
        ##########################################################################################
        #
        # fetch the last order number to create next order number
        #
        
        
        # Define the query to get the last value from the order number column
        query = "SELECT TOP 1 OrderNumber FROM Orders ORDER BY OrderNumber DESC"

        # Execute the query
        cursor.execute(query)

        # Fetch the result
        row = cursor.fetchone()

        # Check if row is not None
        if row:
            order_no = int(row[0])
            if not isinstance(order_no, int) or order_no == 0:
                order_no = 1
                
                # Combine data into a list of dictionaries
                data_list = [
                        {'Item': key, 'Quantity': value, 'dateTime': date_time, 'order_no': order_no, 'ID': i}
                        for i, (key, value) in enumerate(order.items())
                    ]
                
                row = [{'OrderNumber':order_no, 'dateTime': date_time, 'TotalBill': total_cost}]
                
            else:
                # Combine data into a list of dictionaries
                order_no = order_no + 1
                data_list = [
                    {'Item': key, 'Quantity': value, 'dateTime': date_time, 'order_no': order_no, 'ID': i}
                    for i, (key, value) in enumerate(order.items())
                ]
                
                row = [{'OrderNumber':order_no, 'dateTime': date_time, 'TotalBill': total_cost}]
                
        else:
            order_no = 1
            data_list = [
                    {'Item': key, 'Quantity': value, 'dateTime': date_time, 'order_no': order_no, 'ID': i}
                    for i, (key, value) in enumerate(order.items())
                ]
                
            print(f'The last order number is: {order_no}')
            
            row = [{'OrderNumber':order_no, 'dateTime': date_time, 'TotalBill': total_cost}]
            
        
        ##########################################################################################
        #
        # Creating the datarame from the order dictionary values
        #
        

        # Step 4: Create the DataFrame
        df = pd.DataFrame(data_list)
        
        df_revenue = pd.DataFrame(data = row)

        # Display the DataFrame
        print(df)

        robot("If your order is complete, please say hello")
        
        Final = recognize_speech('Say hello to complete the order')
        print(Final)
        
        if Final == 'hello' or Final == 'Hello':
            
            print("Parsed Order:")

            robot("Your final order is shown below")
            
            
            print("Order Number:", order_no)
            
            final_order_text = "Your order number is {}".format(order_no)
            robot(final_order_text)
            
            ##########################################################################################
            #
            # inserting dataframe to local MSSQL database table
            #
            def get_query1():
                query = "INSERT INTO Orders (OrderDate, FoodItem, Quantity, OrderNumber) VALUES (%s, %s, %s, %s)" 
                return query

            
            for index, row in df.iterrows():
                cursor = conn.cursor()
                cursor.execute(get_query1(), (row.dateTime, row.Item, row.Quantity, row.order_no))
                
                conn.commit()
                cursor.close()
                
            print("query executed")
            
            ##########################################################################################
            
            def get_query2():
                query = "INSERT INTO TotalRevenue (OrderDate, OrderNumber, TotalBill) VALUES (%s, %s, %s)" 
                return query

            
            for index, row in df_revenue.iterrows():
                cursor = conn.cursor()
                cursor.execute(get_query2(), (row.dateTime, row.OrderNumber, row.TotalBill))
                
                conn.commit()
                cursor.close()
                
            print("query executed")
            
            print("********************************************************")
            for item, quantity in order.items():
                print(f"{item}: {quantity}")
            print("********************************************************")
            print(f"\nTotal Cost: Rs:{total_cost:.2f}")
            
            #print(Final)
            print("Order Complete")
            break
        
        
    except sr.UnknownValueError:
        print("Sorry, I couldn't understand what you said.")
    except sr.RequestError as e:
        print("Error:", e)
