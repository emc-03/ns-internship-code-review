#Basic Calculator App
This project is a simple calculator application. 
*Important*
It is not yet fully functional, API needs to be tested, missing .env files, and additional CSS implementation.

Includes : 
-React FrontEnd, not fully functional
-Python(FASTAPI) backend for handling calculations
- API Contract, for communication between frontend and backend(services)

Operations : 
Perform basic arithemetic operation: 
-Addition
-Subtraction
-Muliplication
-Division

-Basic Input Validation
-Erorr Handling (divide by zero)
-Uses a functional dictionary to map operators, instead of if else OR switch case 

EndPoints : 
left, right, operator --> response = result 

Application Flow: 
User Input -> Fetch API -> FastAPI Endpoint -> Calculator Logic(uses mapping) -> JSON -> Display Result to UI 
