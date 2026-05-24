from django.contrib import admin
from .models import User, Court, Booking, Product, TrainerProfile, Sale, SaleItem, CashTransaction, ShiftClose

admin.site.site_header = "Бадминтон зала Юнак"
admin.site.site_title = "Бадминтон зала Юнак"
admin.site.index_title = "Административен панел"

admin.site.register(User)
admin.site.register(Court)
admin.site.register(Booking)
admin.site.register(Product)
admin.site.register(TrainerProfile)
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(CashTransaction)
@admin.register(ShiftClose)
class ShiftCloseAdmin(admin.ModelAdmin):
    list_display = ('closed_at', 'cashier', 'sales_total', 'cash_total', 'card_total', 'cash_balance', 'sales_count', 'attendance')
    readonly_fields = ('report_data',)
