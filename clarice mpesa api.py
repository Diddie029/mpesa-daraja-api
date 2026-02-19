"""
M-Pesa Mobile Money Integration Platform
Simplifies mobile money payments for small businesses in Africa
"""

import requests
import base64
import json
from datetime import datetime
from typing import Optional, Dict
import os


class MPesaAPI:
    """
    M-Pesa Daraja API Integration
    Supports STK Push (Lipa na M-Pesa), B2C, and transaction queries
    """
    
    def __init__(self, consumer_key: str, consumer_secret: str, 
                 shortcode: str, passkey: str, environment: str = "sandbox"):
        """
        Initialize M-Pesa API client
        
        Args:
            consumer_key: Your app consumer key from Safaricom
            consumer_secret: Your app consumer secret
            shortcode: Business shortcode
            passkey: Lipa na M-Pesa passkey
            environment: 'sandbox' or 'production'
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.shortcode = shortcode
        self.passkey = passkey
        
        # Set API URLs based on environment
        if environment == "sandbox":
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"
        
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self) -> str:
        """Generate OAuth access token"""
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        
        # Create base64 encoded credentials
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            self.access_token = result['access_token']
            return self.access_token
            
        except Exception as e:
            raise Exception(f"Failed to get access token: {str(e)}")
    
    def stk_push(self, phone_number: str, amount: int, 
                 account_reference: str, transaction_desc: str,
                 callback_url: str) -> Dict:
        """
        Initiate STK Push (Lipa na M-Pesa Online)
        
        Args:
            phone_number: Customer phone number (format: 254XXXXXXXXX)
            amount: Amount to charge
            account_reference: Reference for the transaction
            transaction_desc: Description of transaction
            callback_url: Your callback URL for results
        
        Returns:
            Dict with response data
        """
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"
        
        # Generate timestamp and password
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def query_transaction(self, checkout_request_id: str) -> Dict:
        """
        Query the status of an STK Push transaction
        
        Args:
            checkout_request_id: The CheckoutRequestID from stk_push response
        
        Returns:
            Dict with transaction status
        """
        if not self.access_token:
            self.get_access_token()
        
        url = f"{self.base_url}/mpesa/stkpushquery/v1/query"
        
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}


class TransactionManager:
    """Manage and store transaction records"""
    
    def __init__(self, db_file: str = "transactions.json"):
        self.db_file = db_file
        self.transactions = self._load_transactions()
    
    def _load_transactions(self) -> list:
        """Load transactions from file"""
        try:
            with open(self.db_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def _save_transactions(self):
        """Save transactions to file"""
        with open(self.db_file, 'w') as f:
            json.dump(self.transactions, f, indent=2)
    
    def add_transaction(self, phone: str, amount: int, 
                       reference: str, status: str, 
                       checkout_request_id: str = None):
        """Add a new transaction record"""
        transaction = {
            "id": len(self.transactions) + 1,
            "phone": phone,
            "amount": amount,
            "reference": reference,
            "status": status,
            "checkout_request_id": checkout_request_id,
            "timestamp": datetime.now().isoformat()
        }
        self.transactions.append(transaction)
        self._save_transactions()
        return transaction
    
    def update_transaction_status(self, checkout_request_id: str, 
                                  new_status: str):
        """Update transaction status"""
        for trans in self.transactions:
            if trans.get('checkout_request_id') == checkout_request_id:
                trans['status'] = new_status
                self._save_transactions()
                return True
        return False
    
    def get_transactions(self, phone: Optional[str] = None) -> list:
        """Get all transactions or filter by phone"""
        if phone:
            return [t for t in self.transactions if t['phone'] == phone]
        return self.transactions
    
    def get_daily_revenue(self) -> float:
        """Calculate today's revenue from successful transactions"""
        today = datetime.now().date().isoformat()
        revenue = sum(
            t['amount'] for t in self.transactions
            if t['status'] == 'SUCCESS' and t['timestamp'].startswith(today)
        )
        return revenue


def demo_menu():
    """Interactive demo menu"""
    print("\n" + "="*60)
    print("M-PESA INTEGRATION PLATFORM")
    print("="*60)
    print("\n1. Initialize M-Pesa Client")
    print("2. Send STK Push (Lipa na M-Pesa)")
    print("3. Query Transaction Status")
    print("4. View All Transactions")
    print("5. View Daily Revenue")
    print("6. Exit")
    print("\n" + "="*60)


def main():
    """Main application"""
    print("\n🚀 M-Pesa Mobile Money Integration Platform")
    print("📱 Simplifying payments for African businesses\n")
    
    # Initialize transaction manager
    trans_manager = TransactionManager()
    mpesa_client = None
    
    # Demo credentials (use sandbox credentials here)
    print("⚠️  SETUP REQUIRED:")
    print("Get your API credentials from:")
    print("https://developer.safaricom.co.ke/\n")
    
    while True:
        demo_menu()
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == "1":
            print("\n📝 Initialize M-Pesa Client")
            consumer_key = input("Consumer Key: ").strip() or "DEMO_KEY"
            consumer_secret = input("Consumer Secret: ").strip() or "DEMO_SECRET"
            shortcode = input("Business Shortcode: ").strip() or "174379"
            passkey = input("Passkey: ").strip() or "DEMO_PASSKEY"
            
            mpesa_client = MPesaAPI(
                consumer_key=consumer_key,
                consumer_secret=consumer_secret,
                shortcode=shortcode,
                passkey=passkey,
                environment="sandbox"
            )
            print("✅ M-Pesa client initialized!")
        
        elif choice == "2":
            if not mpesa_client:
                print("❌ Please initialize M-Pesa client first (Option 1)")
                continue
            
            print("\n💳 Send Payment Request")
            phone = input("Phone Number (254XXXXXXXXX): ").strip()
            amount = input("Amount (KES): ").strip()
            reference = input("Account Reference: ").strip()
            description = input("Description: ").strip()
            callback_url = input("Callback URL: ").strip() or "https://yourdomain.com/callback"
            
            try:
                result = mpesa_client.stk_push(
                    phone_number=phone,
                    amount=int(amount),
                    account_reference=reference,
                    transaction_desc=description,
                    callback_url=callback_url
                )
                
                print("\n📤 STK Push Response:")
                print(json.dumps(result, indent=2))
                
                # Save transaction
                if result.get('ResponseCode') == '0':
                    trans_manager.add_transaction(
                        phone=phone,
                        amount=int(amount),
                        reference=reference,
                        status="PENDING",
                        checkout_request_id=result.get('CheckoutRequestID')
                    )
                    print("\n✅ Payment request sent! Customer will receive prompt on phone.")
                
            except Exception as e:
                print(f"❌ Error: {e}")
        
        elif choice == "3":
            if not mpesa_client:
                print("❌ Please initialize M-Pesa client first (Option 1)")
                continue
            
            checkout_id = input("\nCheckoutRequestID: ").strip()
            result = mpesa_client.query_transaction(checkout_id)
            print("\n📊 Transaction Status:")
            print(json.dumps(result, indent=2))
        
        elif choice == "4":
            transactions = trans_manager.get_transactions()
            print(f"\n📋 All Transactions ({len(transactions)} total)\n")
            
            if transactions:
                for t in transactions[-10:]:  # Show last 10
                    print(f"ID: {t['id']} | Phone: {t['phone']} | "
                          f"Amount: KES {t['amount']} | Status: {t['status']} | "
                          f"Time: {t['timestamp'][:19]}")
            else:
                print("No transactions yet.")
        
        elif choice == "5":
            revenue = trans_manager.get_daily_revenue()
            print(f"\n💰 Today's Revenue: KES {revenue:,.2f}")
        
        elif choice == "6":
            print("\n👋 Goodbye! Keep building amazing solutions for Africa!")
            break
        
        else:
            print("❌ Invalid choice. Please try again.")
        
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()