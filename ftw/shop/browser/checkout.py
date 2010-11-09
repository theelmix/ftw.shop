import base64
import simplejson
from datetime import datetime, timedelta

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.z3cform.wizard import wizard
from plone.registry.interfaces import IRegistry
from plone.z3cform.layout import FormWrapper
from z3c.form import field, button
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget
from zope.app.pagetemplate import viewpagetemplatefile as zvptf
from zope.interface import implements, Interface
from zope.component import getMultiAdapter, adapts
from zope.component import getAdapters
from zope.component import getUtility

from ftw.shop.config import SESSION_ADDRESS_KEY, COOKIE_ADDRESS_KEY
from ftw.shop.interfaces import IShopConfiguration
from ftw.shop.interfaces import IDefaultContactInformation
from ftw.shop.interfaces import IContactInformationStep
from ftw.shop.interfaces import IContactInformationStepGroup
from ftw.shop.interfaces import IPaymentProcessor
from ftw.shop.interfaces import IPaymentProcessorChoiceStep
from ftw.shop.interfaces import IPaymentProcessorStepGroup
from ftw.shop.interfaces import IDefaultPaymentProcessorChoice
from ftw.shop.interfaces import IOrderReviewStep
from ftw.shop.interfaces import IOrderReviewStepGroup
from ftw.shop.browser.widgets.paymentprocessor import PaymentProcessorFieldWidget
from ftw.shop import shopMessageFactory as _


class DefaultContactInfoStep(wizard.Step):
    implements(IContactInformationStep)
    prefix = 'contact_information'
    label = _(u"label_default_contact_info_step",
              default="Contact Information")
    title = _(u"title_default_contact_info_step",
              default="Default Contact Information")
    description = _(u'help_default_contact_info_step', default=u"")
    fields = field.Fields(IDefaultContactInformation)
    fields['newsletter'].widgetFactory = SingleCheckBoxFieldWidget

    def __init__(self, context, request, wiz):
        super(wizard.Step, self).__init__(context, request)
        self.wizard = wiz
        PREFILL_FIELDS = ['title', 'firstname', 'lastname', 'email',
                          'street1', 'street2', 'phone', 'zipcode',
                          'city', 'country', 'newsletter']

        if COOKIE_ADDRESS_KEY in request:
            # Prefill contact data with values from cookie
            cookie_data = simplejson.loads(base64.b64decode(
                                    request[COOKIE_ADDRESS_KEY]))
            for key in cookie_data.keys():
                if isinstance(cookie_data[key], basestring):
                    cookie_data[key] = unicode(cookie_data[key])

            for fieldname in PREFILL_FIELDS:
                self.fields[fieldname].field.default = cookie_data[fieldname]

        elif SESSION_ADDRESS_KEY in request.SESSION.keys():
            # Prefill contact data form with values from session
            contact_info = request.SESSION[SESSION_ADDRESS_KEY]
            for fieldname in PREFILL_FIELDS:
                self.fields[fieldname].field.default = contact_info[fieldname]

    def updateWidgets(self):
        super(DefaultContactInfoStep, self).updateWidgets()
        self.widgets['zipcode'].size = 5


class DefaultContactInfoStepGroup(object):
    implements(IContactInformationStepGroup)
    adapts(Interface, Interface, Interface)
    title = _(u"title_default_contact_info_step_group",
              default="Default Contact Information")
    steps = (DefaultContactInfoStep, )

    def __init__(self, context, request, foo):
        pass


class DefaultPaymentProcessorChoiceStep(wizard.Step):
    implements(IPaymentProcessorChoiceStep)
    prefix = 'payment_processor_choice'
    label = _(u"label_default_payment_processor_choice_step",
              default="Payment Processor")
    title = _(u"title_default_payment_processor_step",
              default="Default Payment Processor Choice")
    description = _(u'help_default_payment_processor_choice_step',
                    default=u"")
    fields = field.Fields(IDefaultPaymentProcessorChoice)
    fields['payment_processor'].widgetFactory = PaymentProcessorFieldWidget


class DefaultPaymentProcessorStepGroup(object):
    implements(IPaymentProcessorStepGroup)
    adapts(Interface, Interface, Interface)
    title = _(u"title_default_payment_processor_step_group",
              default="Default Payment Processor Choice")
    steps = (DefaultPaymentProcessorChoiceStep, )

    def __init__(self, context, request, foo):
        pass


class InvoicePaymentProcessor(object):
    implements(IPaymentProcessor)
    adapts(Interface, Interface, Interface)

    external = False
    url = None
    title = "Gegen Rechnung"
    image = """<img src="++resource++ftw-shop-resources/einzahlungsschein.png" />"""
    description = """<em>Bezahlung gegen Rechnung</em>"""

    def __init__(self, context, request, foo):
        pass


class DefaultOrderReviewStep(wizard.Step):
    implements(IOrderReviewStep)
    prefix = 'order-review'
    label = _(u'label_order_review_step', default="Order Review")
    title = _(u"title_default_order_review_step",
              default="Default Order Review Step")
    description = _(u'help_order_review_step', default=u'')
    index = zvptf.ViewPageTemplateFile('templates/checkout/order_review.pt')

    def __init__(self, context, request, wiz):
        super(wizard.Step, self).__init__(context, request)
        self.wizard = wiz

class DefaultOrderReviewStepGroup(object):
    implements(IOrderReviewStepGroup)
    adapts(Interface, Interface, Interface)
    title = _(u"title_default_order_review_step_group",
              default="Default Order Review Step Group")
    steps = (DefaultOrderReviewStep, )

    def __init__(self, context, request, foo):
        pass


class CheckoutWizard(wizard.Wizard):
    label = _(u"label_checkout_wizard", default="Checkout")
    index = zvptf.ViewPageTemplateFile('templates/checkout-wizard.pt')

    def __init__(self, context, request):
        super(CheckoutWizard, self).__init__(context, request)
        self.context = context
        self.request = request

    def getSelectedPaymentProcessor(self):
        payment_processor = None
        if 'payment_processor_choice' not in self.session.keys():
            return None
        try:
            pp_name = self.session.get(
                    'payment_processor_choice').get('payment_processor')
        except KeyError:
            try:
                pp_name = self.request.SESSION.get(
                        'payment_processor_choice').get('payment_processor')
            except KeyError:
                # No payment processor step activated
                pp_name = "none"
        for name, adapter in getAdapters((self.context, None, self.context),
                                         IPaymentProcessor):
            if name == pp_name:
                payment_processor = adapter
        return payment_processor

    @property
    def steps(self):
        contact_info_steps = ()
        contact_info_step_groups = getAdapters(
                                        (self.context, self.request, self),
                                        IContactInformationStepGroup)
        payment_processor_step_groups = getAdapters(
                                        (self.context, self.request, self),
                                        IPaymentProcessorStepGroup)
        order_review_step_groups = getAdapters(
                                        (self.context, self.request, self),
                                        IOrderReviewStepGroup)
        registry = getUtility(IRegistry)
        shop_config = registry.forInterface(IShopConfiguration)

        # Get steps for selected Contact Info Step Group
        selected_contact_info_step_group = shop_config.contact_info_step_group
        for name, step_group_adapter in contact_info_step_groups:
            if name == selected_contact_info_step_group:
                contact_info_steps = step_group_adapter.steps

        # Get steps for selected Payment Processor Step Group
        selected_pp_step_group = shop_config.payment_processor_step_group
        for name, step_group_adapter in payment_processor_step_groups:
            if name == selected_pp_step_group:
                payment_processor_steps = step_group_adapter.steps

        # Get steps for selected Order Review Step Group
        selected_order_review_step_group = shop_config.order_review_step_group
        for name, step_group_adapter in order_review_step_groups:
            if name == selected_order_review_step_group:
                order_review_steps = step_group_adapter.steps

        return contact_info_steps + payment_processor_steps + order_review_steps


    @button.buttonAndHandler(_(u'btn_back', default="Back"),
                             name='back',
                             condition=lambda form: not form.onFirstStep)
    def handleBack(self, action):
        data, errors = self.currentStep.extractData()
        if errors:
            errorMessage ='<ul>'
            for error in errors:
                if errorMessage.find(error.message):
                    errorMessage += '<li>' + error.message + '</li>'
            errorMessage += '</ul>'
            self.status = errorMessage

        else:
            self.currentStep.applyChanges(data)
            self.updateCurrentStep(self.currentIndex - 1)

            # Back can change the conditions for the finish button,
            # so we need to reconstruct the button actions, since we
            # do not redirect.
            self.updateActions()

    @button.buttonAndHandler(_(u'btn_continue', default='Next'),
                             name='continue',
                             condition=lambda form: not form.onLastStep)
    def handleContinue(self, action):
        data, errors = self.currentStep.extractData()
        if errors:
            errorMessage ='<ul>'
            for error in errors:
                if errorMessage.find(error.message):
                    errorMessage += '<li>' + error.message + '</li>'
            errorMessage += '</ul>'
            self.status = errorMessage
        else:

            self.currentStep.applyChanges(data)
            self.updateCurrentStep(self.currentIndex + 1)

            # Proceed can change the conditions for the finish button,
            # so we need to reconstruct the button actions, since we
            # do not redirect.
            self.updateActions()

    @button.buttonAndHandler(_(u'btn_finish', default='Finish'),
             name='finish',
             condition=lambda form: form.allStepsFinished or form.onLastStep)
    def handleFinish(self, action):
        data, errors = self.currentStep.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        else:
            self.status = self.successMessage
            self.finished = True
        self.currentStep.applyChanges(data)
        self.finish()

        self.request.SESSION[SESSION_ADDRESS_KEY] = {}
        self.request.SESSION[SESSION_ADDRESS_KEY].update(
                                        self.session['contact_information'])
        self.request.SESSION['order_confirmation'] = True
        self.request.SESSION['payment_processor_choice'] = {}
        if 'payment_processor_choice' in self.session.keys():
            self.request.SESSION['payment_processor_choice'].update(
                                    self.session['payment_processor_choice'])

        # Save contact information in a cookie in order to prefill
        # form if customer returns
        cookie_value = base64.b64encode(simplejson.dumps(
                                        self.session['contact_information']))
        expiry_date = (datetime.now() + timedelta(days=90)).strftime(
                                                "%a, %d-%b-%Y %H:%M:%S GMT")
        self.request.RESPONSE.setCookie(COOKIE_ADDRESS_KEY,
                                        cookie_value,
                                        expires=expiry_date)

        self.request.SESSION[self.sessionKey] = {}
        self.sync()

        pp = self.getSelectedPaymentProcessor()
        if pp is not None and pp.external:
            self.request.SESSION['external-processor-url'] = pp.url
            self.request.SESSION['external-processor-url'] = "http://localhost:8077/"

        self.request.response.redirect('checkout')


class CheckoutView(FormWrapper):
    #layout = ViewPageTemplateFile("templates/layout.pt")
    #index = layout
    form = CheckoutWizard

    def __init__(self, context, request):
        cart_view = getMultiAdapter((context, request), name='cart_view')
        request['cart_view'] = cart_view
        FormWrapper.__init__(self, context, request)


class ExternalPaymentProcessorView(BrowserView):
    """Redirects to an external payment processor
    """
    __call__ = ViewPageTemplateFile('templates/checkout/external.pt')
