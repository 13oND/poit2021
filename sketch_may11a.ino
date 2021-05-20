// pouzita kniznica https://github.com/br3ttb/Arduino-PID-Library
#include <PID_v1.h>

//Variables
double Input, Output;

//PID Parameters

double Kp = 1, Ki = 0.7, Kd = 0, Setpoint = 500;
int counter = 0;
//String trash = "";

boolean newData = false;

const byte numChars = 32;
char receivedChars[numChars];

//Start PID Instance

PID myPID(&Input, &Output, &Setpoint, Kp, Ki, Kd, DIRECT);

void setup(){

  //Start Serial
  Serial.begin(9600);

  
  //Set point 
  Input = analogRead(A3);  

  //Turn the PID on
  myPID.SetMode(AUTOMATIC);

  //Adjust PID values
  myPID.SetTunings(Kp, Ki, Kd);

}

void loop(){

  recvWithStartEndMarkers();
  showNewData();  
  
  Input = analogRead(A3);  

  //PID calculation

  myPID.Compute();  // toto mi vyrata Output

  //Write the output as calculated by the PID function

  analogWrite(9, Output); 

  delay(200);   // pomalsie vypisovanie

  // if (Setpoint != 500){
  Serial.println((Input/1023)*5);   //toto posielam do raspberry Pi
    
//  Serial.println("-----Kp, Ki, Kd, Setpoint-----");
//  Serial.println(Kp);
//  Serial.println(Ki);
//  Serial.println(Kd);
//  Serial.println(Setpoint);
}

void recvWithStartEndMarkers() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;
 
 // if (Serial.available() > 0) {
    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();
        delayMicroseconds(100);   // added delay 

        if (recvInProgress == true) {
            if (rc != endMarker) {
                receivedChars[ndx] = rc;
                ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }
            else {
                receivedChars[ndx] = '\0'; // terminate the string
                recvInProgress = false;
                ndx = 0;
                newData = true;
            }
        }

        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

void showNewData() {
   if (newData == true) {
   newData = false;
   parseData();
   }
}

void parseData() {
    // split the data into its parts
    
  char * strtokIndx; // this is used by strtok() as an index

  // 1a0.7a0a1000a        str 
  
  strtokIndx = strtok(receivedChars, "a"); // this continues where the previous call left off
  Kp = atof(strtokIndx);     
  
  strtokIndx = strtok(NULL, "a"); 
  Ki = atof(strtokIndx);     // convert this part to a float (double)

  strtokIndx = strtok(NULL, "a"); 
  Kd = atof(strtokIndx);     // convert this part to a float (double)

  strtokIndx = strtok(NULL, "a"); 
  Setpoint = atof(strtokIndx);     // convert this part to a float (double)
}
