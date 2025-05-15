import os, random
import json

#def main():
#    random_challenge=get_and_return_challenge()
#    print(f"Welcome to the vending machine! Here's your random challenge: {random_challenge['name']} \n")
#    print(f"You find details inside of your package! \n")
#    print(f"Difficulty: {random_challenge['difficulty'].title()}")
#    print(f"Description: {random_challenge['description']}")
    
#def get_and_return_challenge() -> dict:
#    with open(os.path.join("challenges", random.choice(os.listdir("challenges"))), 'r') as file:
#            data = json.load(file)
#            return data

#def evaluate_challenge() -> list:
#    solution_file=input("Input the location of your file! ")
#    with open(os.path.abspath(solution_file), 'r') as solution:
#          user_code="".join(solution.readlines())
#    local_scope={}
#    exec(user_code, {"__builtins__": __builtins__}, local_scope)	
#    pass
#if __name__ == "__main__":
#    main()
    


