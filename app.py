from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flasgger import Swagger
from models import db, Subscriber, Bill
from sqlalchemy.exc import IntegrityError
from flask import request,Response
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///billpayment.db'  

db.init_app(app)

api = Api(app)
swagger = Swagger(app)

with app.app_context():
    db.create_all()

def create_sample_data():
    subscriber_data = [
        {'subscriber_number': '1','username': 'elif', 'password': '123', 'user_type' : 'normal'},
        {'subscriber_number': '2','username': 'admin', 'password': '1234', 'user_type' : 'admin'}
    ]

    for data in subscriber_data:
        subscriber = Subscriber.query.filter_by(subscriber_number=data['subscriber_number']).first()
        if subscriber is None:
            subscriber = Subscriber(**data)
            db.session.add(subscriber)
        else:
            print(f"subscriber with subscriber number {data['subscriber_number']} already exists. Skipping...")

    bill_data = [
        {'subscriber_id': 1, 'month': '1', 'bill_total': 1500, 'payment_status': "false", 'remaining_amount' : 0},
        {'subscriber_id': 2, 'month': '5', 'bill_total': 2000, 'payment_status': "true", 'remaining_amount' : 0}
    ]

    for data in bill_data:
        bill = Bill.query.filter_by(subscriber_id=data['subscriber_id']).first()
        if bill is None:
            bill = Bill(**data)
            db.session.add(bill)
        else:
            print(f"Bill details already exist for subscriber ID {data['subscriber_id']}. Skipping...")

    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        print("IntegrityError:", e)


class Login(Resource):
    def post(self):
        """
        User Login
        ---
        tags:
          - auth
        parameters:
          - in: query
            name: username
            type: string
            required: true
            description: The username
          - in: query
            name: password
            type: string
            required: true
            description: The password
                
               
        responses:
          '200':
            description: Login successful
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    message:
                      type: string
                    user_type:
                      type: string
          '401':
            description: Invalid username or password
        """
       
        username = request.args.get('username')
        password = request.args.get('password')


        subscriber = Subscriber.query.filter_by(username=username).first()
        if not subscriber:
             error_message = json.dumps({"error": "Login Unsuccessful"})
             return error_message, 404, {'Content-Type': 'application/json'}

        pass_control = check_password_hash(subscriber.password, password)
        if pass_control != True:
            error_message = json.dumps({"error": "Invalid username or password"})
            return error_message, 401, {'Content-Type': 'application/json'}

        return json.dumps({"message": "Welcome"})
    pass
    
class BankingApp(Resource):
    
    def get(self):
        """
        Get unpaid bill details for a subscriber using banking app
        ---
        tags:
          - banking
        parameters:
          - in: query
            name: subscriber_number
            schema:
              type: string
            required: true
            description: The subscriber number
            
        responses:
          '200':
            description: Unpaid bill details retrieved successfully
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    bills:
                      type: array
                      items:
                        type: object
                        properties:
                          bill_total:
                            type: number
                          payment_status:
                            type: string
                          month : 
                            type : array
          '404':
            description: Subscriber or unpaid bill details not found
            application/json:
              schema:
                
              
        """
        subscriber_number = request.args.get('subscriber_number')
        subscriber = Subscriber.query.filter_by(subscriber_number=subscriber_number).first()
        if not subscriber:

            error_message = json.dumps({"error": "User not found or not a subscriber"})
            return error_message, 404, {'Content-Type': 'application/json'}
        
        unpaid_bills = Bill.query.filter_by(subscriber_id=subscriber.id, payment_status="false").all()
        if not unpaid_bills:

            error_message = json.dumps({"error": "Unpaid bill details not found for this subscriber"})
            return error_message, 404, {'Content-Type': 'application/json'}
          
        bills_list = [{"bill_total": bill.bill_total, "payment_status": bill.payment_status, "month" : list(bill.month)} for bill in unpaid_bills]
        return jsonify({"bills": bills_list})

class MobileProvider(Resource):
    
    def get(self):
        """
        Query bill for a subscriber using mobile provider app
        ---
        tags:
          - mobile_provider
        parameters:
          - in: query
            name: subscriber_number
            schema:
              type: string
            required: true
            description: The subscriber number
          - in: query
            name: month
            schema:
              type: string
            required: true
            description: The month for which bill details are requested
            
        responses:
          '200':
            description: Bill details retrieved successfully
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    bill_total:
                      type: number
                    paid_status:
                      type: boolean
          '404':
            description: Subsciber or bill details not found
        """
        
        subscriber_number = request.args.get('subscriber_number')
        month = request.args.get('month')
        subscriber = Subscriber.query.filter_by(subscriber_number=subscriber_number).first()
        if not subscriber:
            error_message = json.dumps({"error": "User not found or not a subscriber"})
            return error_message, 404, {'Content-Type': 'application/json'}
        
        bill = Bill.query.filter_by(subscriber_id=subscriber.id, month=month).first()
        if not bill:
            error_message = json.dumps({"error": "Bill not found!"})
            return error_message, 404, {'Content-Type': 'application/json'}
        return jsonify({"bill_total": bill.bill_total, "paid_status": bill.payment_status})
    pass

class MobileProviderDetailed(Resource):
    def get(self):
        """
        Query detailed bill for a subscriber using mobile provider app with pagination
        ---
        tags:
          - mobile_provider
        parameters:
          - in: query
            name: subscriber_number
            schema:
              type: string
            required: true
            description: The subscriber number
          - in: query
            name: month
            schema:
              type: string
            required: true
            description: The month for which bill details are requested
            
        responses:
          '200':
            description: Detailed bill details retrieved successfully
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    bills:
                      type: array
                      items:
                        type: object
                        properties:
                          bill_total:
                            type: number
                          paid_status:
                            type: boolean
                          month:
                            type: number
          '404':
            description: Subscriber or bill details not found
        """
       
        subscriber_number = request.args.get('subscriber_number')
        month = request.args.get('month')
        fixed_page = 1  # Fixed page number
        fixed_per_page = 1  # Fixed number of items per page

        subscriber = Subscriber.query.filter_by(subscriber_number=subscriber_number).first()
        if not subscriber:
            error_message = json.dumps({"error": "User not found or not a subscriber"})
            return error_message, 404, {'Content-Type': 'application/json'}

        bills_query = Bill.query.filter_by(subscriber_id=subscriber.id, month=month)
        paginated_bills = bills_query.paginate(page=fixed_page, per_page=fixed_per_page)

        if not paginated_bills.items:
            
            error_message = json.dumps({"error": "Bill details not found for this subscriber and month"})
            return error_message, 404, {'Content-Type': 'application/json'}
            

        bills_list = [{"bill_total": bill.bill_total, "paid_status": bill.payment_status, "month": bill.month} for bill in paginated_bills.items]
        return jsonify({"bills": bills_list, "total_pages": paginated_bills.pages, "current_page": paginated_bills.page})



class WebsitePayBill(Resource):
    def post(self):
        """
        Pay bill for a subscriber using subscriber app
        ---
        tags:
          - website
        parameters:
          - in: body
            name: PayBill
            schema:
              type: object
              properties:
                subscriber_number:
                  type: string
                month:
                  type: string
                paid_amount:
                  type: number
            required: true
            description: Subscriber number, month, and amount paid
        responses:
          '200':
            description: Bill payment successful
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    message:
                      type: string
          '404':
            description: Subscriber or bill details not found
        """
        data = request.get_json()
        subscriber_number = data.get('subscriber_number')
        month = data.get('month')
        paid_amount = data.get('paid_amount')


        subscriber = Subscriber.query.filter_by(subscriber_number=subscriber_number).first()
        if not subscriber:
            error_message = json.dumps({"error": "User not found or not a subscriber"})
            return error_message, 404, {'Content-Type': 'application/json'}
        

        bill = Bill.query.filter_by(subscriber_id=subscriber.id, month=month).first()
        if not bill:
            error_message = json.dumps({"error": "Bill details not found for this subscriber and month"})
            return error_message, 404, {'Content-Type': 'application/json'}
        
        if paid_amount == bill.bill_total:
            bill.payment_status = "true"
        elif paid_amount < bill.remaining_amount:
            remaining_amount = bill.bill_total - paid_amount
            bill.remaining_amount = remaining_amount
            bill.payment_status = "false"
        elif paid_amount == bill.remaining_amount:
            remaining_amount = bill.remaining_amount - paid_amount
            bill.remaining_amount = remaining_amount
            bill.payment_status = "true"
        else:
            error_message = json.dumps({"error": "Paid amount exceeds total bill amount"})
            return error_message, 400, {'Content-Type': 'application/json'}
            
          
        db.session.commit()
        return jsonify({"message": "Bill payment successful"})

class WebsiteAddBillByAdmin(Resource):
    def post(self):
        """
        Add bill for a subscriber by admin
        ---
        tags:
          - website
        parameters:
          - in: body
            name: AddBillByAdmin
            schema:
              type: object
              properties:
                subscriber_number:
                  type: string
                month:
                  type: string
                bill_total:
                  type: number
            required: true
            description: Subscriber number, month, and bill total to be added by admin
        responses:
          '200':
            description: Bill added successfully
            content:
              application/json:
                schema:
                  type: object
                  properties:
                    message:
                      type: string
          '404':
            description: Subscriber not found
        """
        data = request.get_json()
        subscriber_number = data.get('subscriber_number')
        month = data.get('month')
        bill_total = data.get('bill_total')

        subscriber = Subscriber.query.filter_by(subscriber_number=subscriber_number).first()
        if not subscriber:
            error_message = json.dumps({"error": "User not found or not a subscriber"})
            return error_message, 404, {'Content-Type': 'application/json'}
        
        new_bill = Bill(subscriber_id=subscriber.id, month=month, bill_total=bill_total, payment_status="false", remaining_amount = bill_total)
        db.session.add(new_bill)
        db.session.commit()
        return jsonify({"message": "Bill added successfully"})

api.add_resource(Login, '/api/v1/_login')
api.add_resource(BankingApp, '/api/v1/banking/bill')
api.add_resource(MobileProvider, '/api/v1/mobile-provider/query-bill')
api.add_resource(MobileProviderDetailed, '/api/v1/mobile-provider/query-bill-detailed')
api.add_resource(WebsitePayBill, '/api/v1/banking/pay-bill')
api.add_resource(WebsiteAddBillByAdmin, '/api/v1/admin/add-bill')

if __name__ == '__main__':
    app.run(debug=True)
