from django.contrib import admin
from .models import User, Court, Booking, Product, TrainerProfile, Sale, SaleItem, CashTransaction, ShiftClose

admin.site.register(User)
admin.site.register(Court)
admin.site.register(Booking)
admin.site.register(Product)
admin.site.register(TrainerProfile)
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(CashTransaction)
admin.site.register(ShiftClose)
