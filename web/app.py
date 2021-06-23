from flask import Flask, jsonify, request
from flask_restful import Api, Resource
import bcrypt
from pymongo import MongoClient

client = MongoClient("mongodb://db:27017")
db = client.BankAPI
users = db["Users"]

app = Flask(__name__)
api = Api(app)

def UserExists(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


class Register(Resource):
    def post(self):

        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]

        if UserExists(username):
            retJson = {
                "status": 301,
                "message": "User doesn't exist."
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Own": 0,
            "Debt": 0
        })

        retJson = {
            "status": 200,
            "message": "Registration successful."
        }
        return jsonify(retJson)

def verifyPw(username, password):
    if not UserExists(username):
        return False

    hashed_pw = users.find({"Username": username})[0]["Password"]

    if bcrypt.hashpw(password.encode("utf8"), hashed_pw) == hashed_pw:
        return True
    else:
        False
    
def cashOwn(username):
    cash = users.find({"Username": username})[0]["Own"]
    return cash

def debtLeft(username):
    debt = users.find({"Username": username})[0]["Debt"]
    return debt

def generateMsgStatus(status, message):
    retJson = {
        "status": status,
        "message": message
    }
    return retJson

def verifyCred(username, password):
    if not UserExists(username):
        return generateMsgStatus(301, "Invalid username."), True

    correct_pw = verifyPw(username, password)
    if not correct_pw:
        return generateMsgStatus(302, "Invalid password."), True

    return None, False


def updateCashOwn(username, balance):
    users.update({"Username": username},{"$set":{"Own":balance}})

def updateDebtLeft(username, balance):
    users.update({"Username": username},{"$set":{"Debt":balance}})


class Add(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCred(username, password)

        if error:
            return jsonify(retJson)
        
        if money <= 0:
            return jsonify(generateMsgStatus(304, "The amount added must be greater than 0."))

        cash = cashOwn(username)
        money -= 1
        bankCash = cashOwn("Bank")
        updateCashOwn("Bank", bankCash + 1)
        updateCashOwn(username, cash+money)
        return jsonify(generateMsgStatus(200, "Amount added successfully."))


class Transfer(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        to = postedData["to"]
        money = postedData["amount"]

        retJson, error = verifyCred(username, password)

        if error:
            return jsonify(retJson)
        
        cash = cashOwn(username)
        if cash <= 0:
            return jsonify(generateMsgStatus(304, "You're out of cash, my friend."))

        if money <= 0:
            return jsonify(generateMsgStatus(304, "You're out of cash, my friend."))

        if not UserExists(to):
            return jsonify(generateMsgStatus(301, "No such username."))

        cash_from = cashOwn(username)
        cash_to = cashOwn(to)
        bank_cash = cashOwn("Bank")

        updateCashOwn("Bank", bank_cash + 1 )
        updateCashOwn(to, cash_to+ money- 1)
        updateCashOwn(username, cash_from - money)

        return jsonify(generateMsgStatus(200, "Successful transaction."))

class Balance(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        retJson, error = verifyCred(username, password)

        if error:
            return jsonify(retJson)

        retJson = users.find({"Username": username},
         {"Password": 0,
        "_id": 0})[0]
        return jsonify(retJson)

class TakeLoan(Resource): 
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCred(username, password)

        if error:
            return jsonify(retJson)

        cash = cashOwn(username)
        debt = debtLeft(username)
        updateCashOwn(username, cash + money)
        updateDebtLeft(username, debt + money)

        return jsonify(generateMsgStatus(200, "Loan amount successfully added to account."))


class PayLoan(Resource):
    def post(self):
        postedData = request.get_json()
        username = postedData["username"]
        password = postedData["password"]
        money = postedData["amount"]

        retJson, error = verifyCred(username, password)

        if error:
            return jsonify(retJson)

        cash = cashOwn(username)

        if cash < money:
            return jsonify(generateMsgStatus(303, "Not enough cash in the account."))

        debt = debtLeft(username)

        updateCashOwn(username, cash - money)
        updateDebtLeft(username, debt - money)

        return jsonify(generateMsgStatus(200, "Successful loan payment."))

api.add_resource(Register, "/register")
api.add_resource(Add, "/add")
api.add_resource(TakeLoan, "/takeloan")
api.add_resource(Transfer, "/transfer")
api.add_resource(Balance, "/balance")
api.add_resource(PayLoan, "/payloan")

if __name__ == "__main__":
    app.run(host="0.0.0.0")