# SCC Shift Scheduling System
The SCC Shift Scheduling System is a Python-based project designed to simplify and optimize the process of creating shift schedules. The algorithm takes into account various factors such as the persons availability, preferences for certain shifts, and the number of shifts per person. It also considers the capacity of each shift and balances the distribution of persons experience levels and genders across shifts for a diversity and efficiency.

The system uses a simulated annealing algorithm, a probabilistic technique for approximating the global optimum of a given function, to find an optimal solution within a large search space. This algorithm allows the system to not only consider the best immediate move but also to potentially accept less optimal solutions in the early stages of the search process, which helps to avoid being trapped in local optima.

Our goal is to ensure a fair and balanced distribution of shifts among the crew, taking into account their individual needs and preferences as well as the operational requirements of the business.

## Getting Started
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

## Prerequisites
You need Python 3.7.XX to run the following code. You can verify the Python version by typing the following:

```
$ python --version
```
## Setting Up a Virtual Environment
Before you can start installing or using packages in your Python project, you'll need to set up a virtual environment. This will help to prevent any package dependencies from clashing with each other. In your project directory, run the following commands:

```
$ python3 -m venv env
```
This command creates a virtual environment named **env**. You can use any name you prefer.

## Activating a Virtual Environment
Before you can start using the virtual environment, you need to activate it.

For MacOS/Linux, use this:
```
$ source env/bin/activate
```

For Windows, use this:
```
$ .\env\Scripts\activate
```

## Installing Required Packages
After activating the virtual environment, you can install the required packages using this command:

```
(env)$ pip install -r requirements.txt
```
Make sure you have a **requirements.txt** file at the root of your project directory that lists all the Python packages that your project depends on. You can create one using **pip freeze > requirements.txt** if you don't have one already.

## Running the Script
Now, you can run the script using Python. For example, if your script is named **script.py**, you can run it like so:

```
(env)$ python simulatedAnnealing_ref.py
```

## Deactivating a Virtual Environment
Once you are done with your work, you can deactivate the virtual environment by typing **deactivate** in your shell.

```
(env)$ deactivate
```

=======
# SCC_Schichtplan_Algorithmus
