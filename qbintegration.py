from os import access
from pydoc import cli
from urllib import response
from weakref import ReferenceType
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from urllib.parse import parse_qs, urlparse
from quickbooks import QuickBooks
from quickbooks.objects.customer import Customer
from quickbooks.objects.invoice import Invoice
from quickbooks.objects import SalesItemLineDetail,SalesItemLine
from quickbooks.objects import Ref, Address
import database
import datetime



client_id = '<clientid>'
client_secret = '<client_secret>'
redirect_uri = 'http://localhost:5000/'
environment = 'sandbox'

auth_client = AuthClient(client_id, client_secret, redirect_uri, environment)
redirect_url = auth_client.get_authorization_url([Scopes.ACCOUNTING])
url_environment = 'https://sandbox-quickbooks.api.intuit.com'
company_number = '<companyNumber>'

def checkIfTokenValid():

    db = database.get_db()
    token_valid_cur = db.execute('SELECT * FROM auth')
    token_valid = token_valid_cur.fetchone()

    if token_valid is not None:
        last_request_dt = token_valid['last_request_dt']
        refresh_expiry_dt = token_valid['refresh_expiry_dt']
        stored_access_token = token_valid['access_token']
        stored_refresh_token = token_valid['refresh_token']

        lastreq_time_obj = datetime.datetime.strptime(last_request_dt, '%Y-%m-%d %H:%M:%S.%f')
        refexpiry_time_obj = datetime.datetime.strptime(refresh_expiry_dt, '%Y-%m-%d %H:%M:%S.%f')

        last_request_dif = (datetime.datetime.now() - lastreq_time_obj).seconds
        refresh_expires_dif = (datetime.datetime.now() - refexpiry_time_obj).seconds

        new_auth_client = AuthClient(client_id, client_secret, redirect_uri, environment)
        new_auth_client.access_token = stored_access_token
        new_auth_client.refresh_token = stored_refresh_token

        if last_request_dif <= 3600:
            return new_auth_client

        elif ((last_request_dif > 3600) and (refresh_expires_dif > 60)):
            new_auth_client.refresh(refresh_token=stored_refresh_token)
            setLastRequestDt(new_auth_client)
            return new_auth_client
    
    return None


def setLastRequestDt(auth_client):
    db = database.get_db()
    refresh_expiry__secs = auth_client.x_refresh_token_expires_in
    refresh_expiry_dt = (datetime.datetime.now()) + (datetime.timedelta(seconds=refresh_expiry__secs))
    db.execute('DELETE FROM auth')
    db.execute('INSERT INTO auth (access_token,refresh_token,last_request_dt,refresh_expiry_dt) VALUES (?,?,?,?)', [auth_client.access_token,auth_client.refresh_token,datetime.datetime.now(),refresh_expiry_dt])
    db.commit()
    return


def getAuthClient(response_url):

    raw_url = urlparse(response_url)
    url_components = parse_qs(raw_url.query)

    parsed_code = url_components.get('code')[0]
    parsed_realm = url_components.get('realmId')[0]

    auth_client.get_bearer_token(parsed_code, realm_id=parsed_realm)
    setLastRequestDt(auth_client)
  
    return auth_client 

def logout(auth_client):
    db = database.get_db()
    db.execute('delete from auth')
    db.commit()
    auth_client.revoke(token=auth_client.access_token)
    return

class QBCustomer():

    def getAllCustomers(auth_client):

        sdk_connection_client = QuickBooks(auth_client=auth_client,company_id=company_number)
        customer_objects = Customer.filter(Active=True,qb=sdk_connection_client)
        customer_data = Customer.to_dict(customer_objects)
        db = database.get_db()

        for customers in customer_data:
            company_name = customers.get('DisplayName')
            balance = customers.get('Balance')
            
            customer_exists_cur = db.execute('SELECT id FROM customer WHERE id = ?', [customers['Id']])
            customer_exists = customer_exists_cur.fetchone()
            if customer_exists is None:
                db.execute('insert INTO customer (companyName,balance) VALUES (?,?)', [company_name,balance])
        
        db.commit()
        return customer_data

    def insertInvoice(auth_client):

        sdk_connection_client = QuickBooks(auth_client=auth_client,company_id=company_number)

        customer_ref = Customer.get(3, qb=sdk_connection_client).to_ref()
        invoice = Invoice()
        invoice.CustomerRef = customer_ref

        ship_to_address = Address()
        ship_to_address.Line1 = '500 E Walnut Ave'
        ship_to_address.City = 'Fullerton'
        ship_to_address.PostalCode = '92832'

        invoice.ShipAddr = ship_to_address

        line_detail = SalesItemLineDetail()
        line_detail.UnitPrice = 100  # in dollars
        line_detail.Qty = 1  # quantity can be decimal
        line_detail.TaxCodeRef = Ref()
        line_detail.TaxCodeRef.value = 'TAX'

        line = SalesItemLine()
        line.Amount = 100  # in dollars
        line.SalesItemLineDetail = line_detail
        line.Description = "Concrete Pour"

        invoice.Line = [line]

        invoice.save(qb=sdk_connection_client)

        return

        
    
    def getCustomerInvoices(auth_client):

        sdk_connection_client = QuickBooks(auth_client=auth_client,company_id=company_number)
        invoice_objects = Invoice.filter(qb=sdk_connection_client,DocNumber='1038')
        invoice_data = Invoice.to_dict(invoice_objects)

        return invoice_data
        

'''
# If you do not want to use the SDK environment, you can create manual requests to the QB API, with example functions below.  


class QBInvoice():
    
    def getAllInvoices(access_token):
        req_header = {'Authorization': 'Bearer ' + acc_token, 'Accept': 'application/json'}
        api_results = requests.get("{}/v3/company/{}/query?query=select * from Invoice&minorversion=63".format(url_environment, company_number), headers=req_header)
        json_data = json.loads(api_results.text)
        unpacked_data = json_data.get('QueryResponse')
        invoice_data = unpacked_data.get('Invoice') # this has invoice level header
        return invoice_data


    def getInvoice(acc_token,invoice_number):
        req_header = {'Authorization': 'Bearer ' + acc_token, 'Accept': 'application/json'}
        api_results = requests.get("{}/v3/company/{}/query?query=select * from Invoice where DocNumber = '{}'&minorversion=63".format(url_environment,company_number,invoice_number), headers=req_header)
        json_data = json.loads(api_results.text)
        unpacked_data = json_data.get('QueryResponse')
        invoice_data = unpacked_data.get('Invoice') # this has invoice level header
        return invoice_data
'''