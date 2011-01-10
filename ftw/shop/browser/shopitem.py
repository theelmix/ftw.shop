from decimal import Decimal
import simplejson

from Acquisition import aq_inner
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from plone.i18n.normalizer.interfaces import IIDNormalizer
from zope.component import getUtility

from ftw.shop import shopMessageFactory as _
from ftw.shop.interfaces import IVariationConfig


class ShopItemView(BrowserView):
    """Default view for a shop item
    """

    __call__ = ViewPageTemplateFile('templates/shopitem.pt')

    single_item_template = ViewPageTemplateFile('templates/listing/single_item.pt')
    one_variation_template = ViewPageTemplateFile('templates/listing/one_variation.pt')
    two_variations_template = ViewPageTemplateFile('templates/listing/two_variations.pt')

    def getItems(self):
        """Returns a list with this item as its only element,
        so the listing viewlet can treat it like a list of items
        """
        context = aq_inner(self.context)
        return [context]

    def single_item(self, item):
        return self.single_item_template(item=item)

    def one_variation(self, item):
        return self.one_variation_template(item=item)

    def two_variations(self, item):
        return self.two_variations_template(item=item)

    def getItemDatas(self):
        """Returns a dictionary of an item's properties to be used in
        templates. If the item has variations, the variation config is
        also included.
        """
        results = []
        for item in self.getItems():
            assert(item.portal_type == 'ShopItem')
            varConf = IVariationConfig(item)

            has_variations = varConf.hasVariations()

            image = None
            tag = None
            if has_variations:
                skuCode = None
                price = None
            else:
                varConf = None
                skuCode = item.Schema().getField('skuCode').get(item)
                price = item.Schema().getField('price').get(item)

            if image:
                tag = image.tag(scale='tile')

            results.append(dict(title = item.Title(),
                                description = item.Description(),
                                url = item.absolute_url(),
                                imageTag = tag,
                                variants = None,
                                skuCode = skuCode,
                                price = price,
                                uid = item.UID(),
                                varConf = varConf,
                                hasVariations = has_variations))
        return results

    def getVariationsConfig(self):
        """Returns the variation config for the item currently being viewed
        """
        context = aq_inner(self.context)
        variation_config = IVariationConfig(context)
        return variation_config

    def getVarDictsJSON(self):
        """Returns a JSON serialized dict with UID:varDict pairs, where UID
        is the ShopItem's UID and varDict is the item's variation dict.
        This is being used for the compact category view where inactive
        item variations must not be buyable.
        """
        varDicts = {}
        items = self.getItemDatas()
        for item in items:
            uid = item['uid']
            varConf = item['varConf']
            if varConf is not None:
                varDicts[uid] = dict(varConf.getVariationDict())
            else:
                varDicts[uid] = {}

            # Convert Decimals to Strings for serialization
            varDict = varDicts[uid]
            for vkey in varDict.keys():
                i = varDict[vkey]
                for k in i.keys():
                    val = i[k]
                    if isinstance(val, Decimal):
                        val = str(val)
                        i[k] = val

        return simplejson.dumps(varDicts)


class ShopCompactItemView(ShopItemView):
    """Compact view for a shop item
    """

    one_variation_template = ViewPageTemplateFile('templates/listing/one_variation_compact.pt')
    two_variations_template = ViewPageTemplateFile('templates/listing/two_variations_compact.pt')


class EditVariationsView(BrowserView):
    """View for editing ShopItem Variations
    """
    template = ViewPageTemplateFile('templates/edit_variations.pt')

    def __call__(self):
        """
        Self-submitting form that displays ShopItem Variations
        and updates them

        """
        form = self.request.form

        # Make sure we had a proper form submit, not just a GET request
        submitted = form.get('form.submitted', False)
        if submitted:
            variation_config = IVariationConfig(self.context)

            edited_var_data = self._parse_edit_variations_form()
            variation_config.updateVariationConfig(edited_var_data)

            IStatusMessage(self.request).addStatusMessage(
                _(u'msg_variations_saved',
                  default=u"Variations saved."), type="info")
            self.request.RESPONSE.redirect(self.context.absolute_url())

        return self.template()

    def _parse_edit_variations_form(self):
        """Parses the form the user submitted when editing variations,
        and returns a dictionary that contains the variation data.
        """
        form = self.request.form
        variation_config = IVariationConfig(self.context)
        variation_data = {}
        normalize = getUtility(IIDNormalizer).normalize

        def _parse_data(variation_key):
            data = {}
            data['active'] = bool(form.get("%s-active" % variation_key))
            # TODO: Handle decimal more elegantly
            price = form.get("%s-price" % variation_key)
            try:
                p = int(price)
                # Create a tuple of ints from string
                digits = tuple([int(i) for i in list(str(p))]) + (0, 0)
                data['price'] = Decimal((0, digits, -2))
            except ValueError:
                if not price == "":
                    data['price'] = Decimal(price)
                else:
                    data['price'] = Decimal("0.00")

            data['skuCode'] = form.get("%s-skuCode" % variation_key)
            data['description'] = form.get("%s-description" % variation_key)

            # At this point the form has already been validated,
            # so uniqueness of sku codes is ensured
            data['hasUniqueSKU'] = True
            return data


        if len(variation_config.getVariationAttributes()) == 1:
            # One variation attribute
            for var1_value in variation_config.getVariation1Values():
                variation_key = normalize(var1_value)

                variation_data[variation_key] = _parse_data(variation_key)
        else:
            # Two variation attributes
            for var1_value in variation_config.getVariation1Values():
                for var2_value in variation_config.getVariation2Values():
                    variation_key = normalize("%s-%s" % (var1_value,
                                                         var2_value))
                    variation_data[variation_key] = _parse_data(variation_key)
        return variation_data

    def getVariationsConfig(self):
        """Returns the variation config for the item being edited
        """
        context = aq_inner(self.context)
        variation_config = IVariationConfig(context)
        return variation_config
