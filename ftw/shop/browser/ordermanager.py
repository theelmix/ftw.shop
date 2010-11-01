from DateTime import DateTime
from datetime import datetime
from email.Utils import formataddr

import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import noSecurityManager
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.utils import getToolByName
from plone.registry.interfaces import IRegistry
from zope.component import getUtility, getMultiAdapter

from ftw.shop.config import SESSION_ADDRESS_KEY
from ftw.shop.model.order import Order
from ftw.shop.model.cartitems import CartItems
from ftw.shop.exceptions import MissingCustomerInformation
from ftw.shop.exceptions import MissingOrderConfirmation
from ftw.shop.interfaces import IMailHostAdapter
from ftw.shop.interfaces import IShopConfiguration
from ftw.shop.utils import create_session


class OrderManagerView(BrowserView):
    """Lists orders stored with SQLAlchemy
    """

    __call__ = ViewPageTemplateFile('templates/order_manager.pt')

    def getOrders(self):
        sa_session = create_session()
        orders = sa_session.query(Order)
        return orders

    def addOrder(self):
        """Add a new Order and return the order id.
        """

        session = self.context.REQUEST.SESSION

        # check for cart
        cart_view = getMultiAdapter((self, self.context.REQUEST),
                                    name=u'cart_view')
        cart_data = cart_view.cart_items()

        # check for customer data
        customer_data = session.get(SESSION_ADDRESS_KEY, {})
        if not customer_data:
            raise MissingCustomerInformation

        # check for order confirmation
        if not session.get('order_confirmation', None):
            raise MissingOrderConfirmation

        # change security context to owner
        user = self.context.getWrappedOwner()
        newSecurityManager(self.context.REQUEST, user)

        # create Order
        sa_session = create_session()
        order = Order()
        sa_session.add(order)
        transaction.commit()

        order_id = order.order_id

        # calc order number
        now = DateTime()
        order_prefix = '%03d%s' % (now.dayOfYear() + 500, now.yy())
        order_number = '%s%04d' % (order_prefix, order_id)
        order.title = order_number

        order.date = datetime.now()
        sa_session.add(order)
        transaction.commit()

        # store customer data
        for key in customer_data.keys():
            try:
                setattr(order, 'customer_%s' % key, customer_data[key])
            except AttributeError:
                pass

        # store cart in order
        for skuCode in cart_data.keys():
            cart_items = CartItems()
            sa_session.add(cart_items)
            cart_items.skuCode = skuCode
            cart_items.quantity = cart_data[skuCode]['quantity']
            cart_items.order_id = order.order_id
            cart_items.order = order
            sa_session.add(cart_items)


        order.cart_contents = cart_data
        order.total = cart_view.cart_total()

        sa_session.add(order)
        transaction.commit()

        noSecurityManager()

        return order_id

    def sendOrderMail(self, order_id):
        """
        Send order confirmation mail of the order with the specified order_id.
        Can be used if initial sending of order mail failed for some reason.
        """
        sa_session = create_session()
        order = sa_session.query(Order).filter_by(order_id=order_id).first()

        fullname = "%s %s" % (order.customer_firstname,
                              order.customer_lastname)

        ltool = getToolByName(self.context, 'portal_languages')
        lang = ltool.getPreferredLanguage()

        registry = getUtility(IRegistry)
        shop_config = registry.forInterface(IShopConfiguration)

        # Send order confirmation mail to customer
        mailTo = formataddr((fullname, order.customer_email))

        if shop_config is not None:
            mailFrom = shop_config.shop_email
            mailBcc = getattr(shop_config, 'mail_bcc', '')
            shop_name = shop_config.shop_name
            mailSubject = getattr(shop_config, 'mail_subject_%s' % lang)
            if not mailSubject:
                mailSubject = '%s Webshop' % shop_name

        mhost = IMailHostAdapter(self.context)
        mail_view = getMultiAdapter((self.context, self.context.REQUEST),
                                    name=u'mail_view')
        msg_body = mail_view(order=order)

        mhost.send(msg_body,
                     mto=mailTo,
                     mfrom=mailFrom,
                     mbcc=mailBcc,
                     subject=mailSubject,
                     encode=None,
                     immediate=False,
                     msg_type='text/html',
                     charset='utf8')

        # Send mail to shop owner about the order
        mailTo = formataddr(("Shop Owner", shop_config.shop_email))

        if shop_config is not None:
            shop_name = shop_config.shop_name
            mailFrom = formataddr((shop_name, shop_config.shop_email))
            mailBcc = getattr(shop_config, 'mail_bcc', '')
            mailSubject = '[%s] Order %s by %s' % (shop_name,
                                                   order_id,
                                                   fullname)

        mhost = IMailHostAdapter(self.context)
        mail_view = getMultiAdapter((self.context, self.context.REQUEST),
                                    name=u'mail_view')
        msg_body = mail_view(order=order)

        mhost.send(msg_body,
                     mto=mailTo,
                     mfrom=mailFrom,
                     mbcc=mailBcc,
                     subject=mailSubject,
                     encode=None,
                     immediate=False,
                     msg_type='text/html',
                     charset='utf8')
        return
