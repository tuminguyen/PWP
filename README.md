# PWP SPRING 2022
# BYC - Book Your Court

![BYCHomepage](uploads/homepage.png)

# Group information
* Student 1. Huong Nguyen _(Huong.Nguyen@oulu.fi)_
* Student 2. Vandana Yadav _(vandana.mj24@gmail.com)_

# Setup
### Install required packages
You can install the required packages inside your [Anaconda](https://docs.anaconda.com/anaconda/install/index.html) or any virtual environments or even directly on your machine using pip command 
```
# Python version: 3.7.6
pip install -r requirements.txt 
```

# Run and Test

### Run
1. Open terminal / command prompt 
2. Clone the project
    ```
    git clone https://github.com/tuminguyen/PWP
    ```
    or directly download the [deliverable5](https://github.com/tuminguyen/PWP/releases/tag/deliverable5) package.
3. By default, the scripts are executable. However, in case of needed, you can make them doable by running the command
    ```
    # On Linux
    chmod +x run.sh
    chmod +x delete_db.sh
    ```
    For Windows users, follow [this tuitorial](https://www.educative.io/edpresso/what-is-chmod-in-windows) to change the permission to the files.

4. If db/ folder does not exist in the project, create the new one before running the program. Otherwise, skip this step.
    ```
    mkdir db
    ```

5. Run the program

    Please populate the database **ONCE at the first time** you run the program.
    ```
    # On Linux
    ./run.sh -p true
    ```
    For the next time you run the program, run it with the populate mode set to __false__. 
    Otherwise, data might be duplicated and violate the UNIQUE constraint.
    ```
    # On Linux
    ./run.sh -p false
    ```

6. Open your browser and access 127.0.0.1:5000
7. Delete all tables and database whenever you want by executing
    ```
    # On Linux
    ./delete_db.sh
    ```

**!! NOTE:** The instruction is written for users with Linux-based systems. However, if you are a Windows users, you can also follow the same commands after installing [cygwin](http://www.cygwin.com/) or [git-bash](https://git-scm.com/downloads).

### Test

There are test files for resources and models. To run the tests, use the below command
```
# On Linux / Windows
pytest
```
After running, you will see the number of passed cases, warning and test coverage value.

---
# Useful links
[Online APIs documentation](https://book-your-court.herokuapp.com/apidocs/)
