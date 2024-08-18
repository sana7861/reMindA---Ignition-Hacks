#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// Create an instance of the LCD class with the I2C address 0x27 and 16 columns x 2 rows
LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  // Initialize the LCD
  lcd.init();
  lcd.backlight();
  
  // Begin serial communication with the baud rate of 9600
  Serial.begin(9600);
}

void loop() {
  // Check if data is available on the serial port
  if (Serial.available() > 0) {
    // Read the incoming data
    String message = Serial.readStringUntil('\n');
    
    // Split the message into name and relationship using comma as delimiter
    int commaIndex = message.indexOf(',');
    String name = message.substring(0, commaIndex);
    String relationship = message.substring(commaIndex + 1);
    
    // Clear the LCD display
    lcd.clear();
    
    // Display the name on the first line
    lcd.setCursor(0, 0);
    lcd.print(name);
    
    // Display the relationship on the second line
    lcd.setCursor(0, 1);
    lcd.print(relationship);
    
    // Wait for a short period to allow the message to be read
    delay(3000); // Adjust delay as needed
  }
}
