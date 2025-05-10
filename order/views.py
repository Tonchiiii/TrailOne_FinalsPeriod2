from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from order.models import Shipment,ShipmentItem  # Import Shipment model
from authentication.models import Users  # Import Users model
from django.template.loader import get_template
import csv
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseNotFound, HttpResponse, HttpResponseForbidden, HttpResponseRedirect, Http404
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import Shipment, Users

def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('login')

    # Fetch the user role and user_id from the session
    user_role = request.session.get('user_role', 'Guest')
    user_id = request.session.get('user_id')  # Assuming user_id is stored in the session

    # Fetch the 5 most recent completed deliveries (status = 'delivered')
    if user_role == 'CLIENT':
        completed_deliveries = Shipment.objects.filter(status='delivered', user_id=user_id).order_by('-created_at')[:5]
    else:
        completed_deliveries = Shipment.objects.filter(status='delivered').order_by('-created_at')[:5]

    # Fetch the 5 most recent pending deliveries (statuses could be 'shipped', 'arrived_at_destination', etc.)
    if user_role == 'CLIENT':
        pending_deliveries = Shipment.objects.filter(
            status__in=['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review'],
            user_id=user_id
        ).order_by('-created_at')[:5]
    else:
        pending_deliveries = Shipment.objects.filter(
            status__in=['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review']
        ).order_by('-created_at')[:5]

    def calculate_totals(shipments):
        for shipment in shipments:
            total_quantity = sum(item.quantity or 0 for item in shipment.items.all())
            total_missing = sum(item.missing or 0 for item in shipment.items.all())

            shipment.total_quantity = total_quantity
            shipment.total_missing = total_missing  # Add total missing quantity

        return shipments

    completed_deliveries = calculate_totals(completed_deliveries)
    pending_deliveries = calculate_totals(pending_deliveries)

    user_name = request.session.get('user_name', 'Guest')

    # Pass the data to the template
    return render(request, 'dashboard.html', {
        'completed_deliveries': completed_deliveries,
        'pending_deliveries': pending_deliveries,
        'user_name': user_name,
        'user_role': user_role,
    })

def view_create_orders(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    clients = Users.objects.filter(role='CLIENT')  # Fetch users with role 'CLIENT'

    return render(request, 'orders/view_create_orders.html', {
        'clients': clients
    })

def view_track_orders(request):
    # Get the status filter from the GET request, if provided
    status_filter = request.GET.get('status', None)

    # Start with all shipments or filter by user_id if CLIENT
    if request.session.get('user_role') == 'CLIENT':
        user_id = request.session.get('user_id')
        shipments = Shipment.objects.filter(user_id=user_id)
        users = Users.objects.filter(id=user_id)
    else:
        shipments = Shipment.objects.all()

    if status_filter:
        shipments = shipments.filter(status=status_filter)
        users = users.filter(status=status_filter)

    shipments = shipments.order_by('-shipment_id', '-created_at')

    # Function to calculate total quantities for each shipment
    def calculate_totals(shipments):
        for shipment in shipments:
            total_quantity = sum(item.quantity for item in shipment.items.all())
            shipment.total_quantity = total_quantity
        return shipments

    shipments = calculate_totals(shipments)

    # Pagination
    paginator = Paginator(shipments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Totals
    total_missing = sum(s.total_quantity for s in page_obj.object_list if s.status == 'pending')
    total_delivered = sum(s.total_quantity for s in page_obj.object_list if s.status == 'delivered')

    return render(request, 'orders/view_track_orders.html', {
        'page_obj': page_obj,
        'total_missing': total_missing,
        'total_delivered': total_delivered,
        'status_filter': status_filter,
    })

def create_order(request):
    if request.method == 'POST':
        # Retrieve the uploaded CSV file
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, "No CSV file uploaded.")
            return redirect('view_create_orders')
        
        # 🔴 Enforce 30MB limit
        if csv_file.size > 30 * 1024 * 1024:
            messages.error(request, "CSV file exceeds the 30MB limit.")
            return redirect('view_create_orders')

        try:
            # Read the CSV file
            csv_data = csv_file.read().decode('utf-8')
            lines = csv_data.splitlines()
            reader = csv.reader(lines)

            # Skip header row
            next(reader)

            descriptions = []
            quantities = []

            # Process each row
            for row in reader:
                if len(row) < 2:
                    continue  # Skip if the row doesn't have at least two columns (Description, Quantity)
                description = row[0].strip()
                quantity = row[1].strip()

                # Add to descriptions and quantities lists
                descriptions.append(description)
                quantities.append(quantity)

            # Validate rows (your validation logic)
            items = []
            for desc, qty in zip(descriptions, quantities):
                if not desc or not qty:
                    continue  # Skip empty rows
                if not qty.isdigit():
                    messages.error(request, f"Invalid quantity: {qty}")
                    return redirect('view_create_orders')
                if any(c in desc for c in ['<', '>', '"', "'"]):  # Forbidden characters check
                    messages.error(request, f"Invalid characters in description: {desc}")
                    return redirect('view_create_orders')

                items.append({
                    'description': desc,
                    'quantity': int(qty),
                })

            # If no valid items were found
            if not items:
                messages.error(request, "No valid items found in the CSV.")
                return redirect('view_create_orders')

            # Create the shipment and items
            client_id = request.POST.get('client')
            client = Users.objects.get(pk=client_id)

            shipment = Shipment.objects.create(user=client, status='shipped')
            for item in items:
                ShipmentItem.objects.create(
                    shipment=shipment,
                    description=item['description'],
                    quantity=item['quantity'],
                    missing=0
                )

            messages.success(request, "Shipment created successfully.", extra_tags='shipment_created')
    
            return redirect('view_track_orders')
        except Exception as e:
            messages.error(request, f"Error processing CSV: {e}")

            return redirect('view_create_orders')

def view_track_order_detail(request, id):
    if not request.session.get('user_id'):
        return redirect('login')

    try:
        shipment = Shipment.objects.get(shipment_id=id)
    except Shipment.DoesNotExist:
        return HttpResponseNotFound("Http Response 404: Shipment not found.")

    # Restrict CLIENT users to only their own shipments
    if request.session.get('user_role') == 'CLIENT':
        if shipment.user_id != request.session.get('user_id'):
            return HttpResponseForbidden("Http Response 403: You are not allowed to view this shipment.")

    STATUS_SEQUENCE = ['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review']
    
    # Calculate the next status
    if shipment.status != 'under_review':
        try:
            current_status_index = STATUS_SEQUENCE.index(shipment.status)
            next_status = STATUS_SEQUENCE[current_status_index + 1] if current_status_index + 1 < len(STATUS_SEQUENCE) else None
        except ValueError:
            next_status = None
    else:
        next_status = None

    total_missing = sum(item.missing for item in shipment.items.all())
    total_quantity = sum(item.quantity for item in shipment.items.all())

    return render(request, 'orders/view_track_order_details.html', {
        'shipment': shipment,
        'next_status': next_status,
        'total_quantity': total_quantity,
        'missing_quantity': total_missing,
    })

def change_shipment_status(request, shipment_id):
    # Get the shipment
    shipment = get_object_or_404(Shipment, shipment_id=shipment_id)
    
    # Ensure that the user is logged in and has permission to change the status
    if not request.session.get('user_id'):
        return redirect('login')

    # Get the next status
    STATUS_SEQUENCE = ['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review']
    current_status_index = STATUS_SEQUENCE.index(shipment.status)

    if current_status_index + 1 < len(STATUS_SEQUENCE):
        next_status = STATUS_SEQUENCE[current_status_index + 1]
        shipment.status = next_status
        shipment.save()

        # Add a success message with shipment name or ID
        shipment_name = shipment.shipment_id  # You can replace this with any field like `shipment.name` if available
        messages.success(request, f"Shipment {shipment_name} status has been successfully updated to {next_status.replace('_', ' ').title()}.")

    return redirect('view_track_order_detail', id=shipment.shipment_id)

def submit_missing_items(request, shipment_id):
    if request.method == 'POST':
        shipment = get_object_or_404(Shipment, shipment_id=shipment_id)

        if request.session.get('user_role') == 'CLIENT':
            if shipment.user_id != request.session.get('user_id'):
                return HttpResponseForbidden("Http Response 403: You are not allowed to view this shipment.")

        if request.session.get('user_role') != 'CLIENT' or shipment.status != 'under_review':
            return HttpResponseForbidden("Http Response 403: You are not allowed to view this shipment.")

        has_error = False

        for item in shipment.items.all():
            missing_key = f'missing_qty_{item.id}'
            missing_value = request.POST.get(missing_key)

            if missing_value is not None and missing_value.strip() != '':
                try:
                    missing_int = int(missing_value)
                    if missing_int < 0:
                        messages.error(request, f"Missing quantity for item {item.description} cannot be less than 0.", extra_tags='missing_data_error')
                        has_error = True
                    elif missing_int > item.quantity:
                        messages.error(request, f"Missing quantity for item {item.description} cannot exceed its quantity ({item.quantity}).", extra_tags='missing_data_error')
                        has_error = True
                    else:
                        item.missing = missing_int
                        item.save()
                except ValueError:
                    messages.error(request, f"Invalid input for item {item.description}. Must be a number.", extra_tags='missing_data_error')
                    has_error = True

        if has_error:
            return redirect('view_track_order_detail', id=shipment.shipment_id)

        shipment.status = 'delivered'
        shipment.save()

        messages.success(request, "Status updated to delivered", extra_tags='status_to_delivered')
        return redirect('view_track_order_detail', id=shipment.shipment_id)

def custom_404(request, exception):
    return render(request, '404.html', {}, status=404)



#Report Generation
def generate_shipment_report(request, shipment_id):
    shipment = Shipment.objects.select_related('user').prefetch_related('items').get(pk=shipment_id)

    html_string = render_to_string('orders/shipment_report.html', {'shipment': shipment})
    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename=shipment_{shipment.shipment_id}_report.pdf'
    return response
