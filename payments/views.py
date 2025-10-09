
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.contrib import messages
import requests
import json
import hmac
import hashlib
from .models import Payment, PaymentType, PaymentHistory

# Paystack Configuration
PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
PAYSTACK_PUBLIC_KEY = settings.PAYSTACK_PUBLIC_KEY
PAYSTACK_INITIALIZE_URL = "https://api.paystack.co/transaction/initialize"
PAYSTACK_VERIFY_URL = "https://api.paystack.co/transaction/verify/"


@login_required
def payment_page(request):
    """Display payment options and form"""
    payment_types = PaymentType.objects.filter(is_active=True)
    user_payments = Payment.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    context = {
        'payment_types': payment_types,
        'user_payments': user_payments,
        'paystack_public_key': PAYSTACK_PUBLIC_KEY,
    }
    return render(request, 'payments/payment_page.html', context)


@login_required
def initialize_payment(request):
    """Initialize payment with Paystack"""
    if request.method == 'POST':
        payment_type_id = request.POST.get('payment_type')
        email = request.POST.get('email', request.user.email)
        phone = request.POST.get('phone', '')
        
        # Validate payment type
        try:
            payment_type = PaymentType.objects.get(id=payment_type_id, is_active=True)
        except PaymentType.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid payment type selected'
            }, status=400)
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            payment_type=payment_type,
            amount=payment_type.amount,
            email=email,
            phone=phone,
            status='pending'
        )
        
        # Initialize payment with Paystack
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Build callback URL
        callback_url = request.build_absolute_uri('/payment/verify/')
        
        data = {
            'email': email,
            'amount': int(float(payment.amount) * 100),  # Convert to kobo (Naira cents)
            'reference': str(payment.reference),
            'callback_url': callback_url,
            'metadata': {
                'user_id': request.user.id,
                'username': request.user.username,
                'payment_type': payment_type.name,
                'phone': phone,
                'custom_fields': [
                    {
                        'display_name': 'Payment Type',
                        'variable_name': 'payment_type',
                        'value': payment_type.name
                    },
                    {
                        'display_name': 'Student Name',
                        'variable_name': 'student_name',
                        'value': request.user.get_full_name() or request.user.username
                    }
                ]
            }
        }
        
        try:
            response = requests.post(
                PAYSTACK_INITIALIZE_URL,
                headers=headers,
                json=data,
                timeout=10
            )
            response_data = response.json()
            
            if response_data.get('status'):
                # Log initialization
                PaymentHistory.objects.create(
                    payment=payment,
                    status='initialized',
                    note='Payment initialized with Paystack'
                )
                
                # Return authorization URL
                return JsonResponse({
                    'status': 'success',
                    'authorization_url': response_data['data']['authorization_url'],
                    'access_code': response_data['data']['access_code'],
                    'reference': str(payment.reference)
                })
            else:
                # Payment initialization failed
                error_message = response_data.get('message', 'Payment initialization failed')
                payment.mark_as_failed({'error': error_message})
                
                PaymentHistory.objects.create(
                    payment=payment,
                    status='failed',
                    note=f'Initialization failed: {error_message}'
                )
                
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                }, status=400)
                
        except requests.exceptions.Timeout:
            payment.mark_as_failed({'error': 'Request timeout'})
            return JsonResponse({
                'status': 'error',
                'message': 'Request timeout. Please try again.'
            }, status=500)
            
        except requests.exceptions.RequestException as e:
            payment.mark_as_failed({'error': str(e)})
            return JsonResponse({
                'status': 'error',
                'message': 'Network error. Please check your connection and try again.'
            }, status=500)
            
        except Exception as e:
            payment.mark_as_failed({'error': str(e)})
            return JsonResponse({
                'status': 'error',
                'message': f'An unexpected error occurred: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)


@login_required
def verify_payment(request):
    """Verify payment after redirect from Paystack"""
    reference = request.GET.get('reference')
    
    if not reference:
        messages.error(request, 'No payment reference provided')
        return redirect('payment_page')
    
    # Get payment record
    try:
        payment = Payment.objects.get(reference=reference)
    except Payment.DoesNotExist:
        messages.error(request, 'Payment record not found')
        return redirect('payment_page')
    
    # Check if already verified
    if payment.status == 'success':
        messages.info(request, 'This payment has already been verified')
        return redirect('payment_page')
    
    # Verify with Paystack
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
    }
    
    try:
        response = requests.get(
            f"{PAYSTACK_VERIFY_URL}{reference}",
            headers=headers,
            timeout=10
        )
        response_data = response.json()
        
        if response_data.get('status') and response_data.get('data'):
            payment_data = response_data['data']
            
            # Check if payment was successful
            if payment_data.get('status') == 'success':
                # Verify amount matches
                amount_paid = float(payment_data.get('amount', 0)) / 100  # Convert from kobo
                
                if amount_paid >= float(payment.amount):
                    # Payment successful
                    payment.mark_as_success(payment_data)
                    
                    PaymentHistory.objects.create(
                        payment=payment,
                        status='success',
                        note='Payment verified successfully'
                    )
                    
                    messages.success(
                        request,
                        f'Payment of ₦{payment.amount:,.2f} successful! Transaction Reference: {reference}'
                    )
                else:
                    # Amount mismatch
                    payment.mark_as_failed(payment_data)
                    
                    PaymentHistory.objects.create(
                        payment=payment,
                        status='failed',
                        note=f'Amount mismatch. Expected: {payment.amount}, Paid: {amount_paid}'
                    )
                    
                    messages.error(request, 'Payment amount mismatch. Please contact support.')
            else:
                # Payment failed or abandoned
                payment.status = payment_data.get('status', 'failed')
                payment.gateway_response = payment_data
                payment.save()
                
                PaymentHistory.objects.create(
                    payment=payment,
                    status=payment.status,
                    note=f'Payment status: {payment_data.get("status")}'
                )
                
                messages.error(
                    request,
                    f'Payment was not successful. Status: {payment_data.get("status", "unknown")}'
                )
        else:
            # Invalid response from Paystack
            payment.mark_as_failed(response_data)
            
            PaymentHistory.objects.create(
                payment=payment,
                status='failed',
                note='Invalid response from payment gateway'
            )
            
            messages.error(request, 'Payment verification failed. Please contact support.')
            
    except requests.exceptions.Timeout:
        messages.error(request, 'Verification timeout. Your payment may still be processing.')
        
    except requests.exceptions.RequestException as e:
        messages.error(request, f'Network error during verification: {str(e)}')
        
    except Exception as e:
        messages.error(request, f'An error occurred during verification: {str(e)}')
    
    return redirect('payment_page')


@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook notifications"""
    if request.method == 'POST':
        # Verify webhook signature
        paystack_signature = request.headers.get('X-Paystack-Signature')
        
        if not paystack_signature:
            return HttpResponse('No signature', status=400)
        
        # Compute hash
        computed_signature = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            request.body,
            hashlib.sha512
        ).hexdigest()
        
        # Verify signature matches
        if computed_signature != paystack_signature:
            return HttpResponse('Invalid signature', status=400)
        
        # Process webhook data
        try:
            data = json.loads(request.body)
            event = data.get('event')
            
            if event == 'charge.success':
                # Payment successful
                reference = data['data']['reference']
                
                try:
                    payment = Payment.objects.get(reference=reference)
                    
                    if payment.status != 'success':
                        payment.mark_as_success(data['data'])
                        
                        PaymentHistory.objects.create(
                            payment=payment,
                            status='webhook_success',
                            note='Payment confirmed via webhook'
                        )
                except Payment.DoesNotExist:
                    pass  # Log this if needed
                    
            elif event == 'charge.failed':
                # Payment failed
                reference = data['data']['reference']
                
                try:
                    payment = Payment.objects.get(reference=reference)
                    payment.mark_as_failed(data['data'])
                    
                    PaymentHistory.objects.create(
                        payment=payment,
                        status='webhook_failed',
                        note='Payment failed (webhook notification)'
                    )
                except Payment.DoesNotExist:
                    pass
            
            return HttpResponse('OK', status=200)
            
        except json.JSONDecodeError:
            return HttpResponse('Invalid JSON', status=400)
        except Exception as e:
            return HttpResponse(f'Error: {str(e)}', status=500)
    
    return HttpResponse('Method not allowed', status=405)


@login_required
def payment_history(request):
    """View user's payment history"""
    payments = Payment.objects.filter(user=request.user).select_related('payment_type').order_by('-created_at')
    
    # Calculate statistics
    total_paid = sum(p.amount for p in payments if p.status == 'success')
    successful_payments = payments.filter(status='success').count()
    pending_payments = payments.filter(status='pending').count()
    
    context = {
        'payments': payments,
        'total_paid': total_paid,
        'successful_payments': successful_payments,
        'pending_payments': pending_payments,
    }
    return render(request, 'payments/history.html', context)


