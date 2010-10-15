from archetypes.schemaextender.field import ExtensionField
from archetypes.schemaextender.interfaces import ISchemaExtender

from zope.component import adapts
from zope.interface import implements

from ftw.shop import shopMessageFactory as _
from ftw.shop.interfaces import IShopItem

from Products.Archetypes import atapi

from Products.ATContentTypes.config import HAS_LINGUA_PLONE
if HAS_LINGUA_PLONE:
    from Products.LinguaPlone.public import StringField
    from Products.LinguaPlone.public import FixedPointField
    from Products.LinguaPlone.public import registerType
else:
    from Products.Archetypes.atapi import StringField
    from Products.Archetypes.atapi import FixedPointField
    from Products.Archetypes.atapi import registerType


class ExtStringField(ExtensionField, StringField):
    """A string field."""
    
class ExtFixedPointField(ExtensionField, FixedPointField):
    """A fixed point field."""


class ShopItemExtender(object):
    """Extends the base type ShopItem with fields `price`
    and `skuCode`.
    """
    implements(ISchemaExtender)
    adapts(IShopItem)

    
    fields = [
        ExtFixedPointField('price',
            default = "0.00",
            required = 0,
            languageIndependent=True,
            widget = atapi.DecimalWidget(
                label = _(u"label_price", default=u"Price"),
                description = _(u"desc_price", default=u""),
                size=8,
            ),
        ),

        ExtStringField('skuCode',
            required = 1,
            languageIndependent=True,
            widget = atapi.StringWidget(
                label = _(u"label_sku_code", default=u"SKU code"),
                description = _(u"desc_sku_code", default=u""),
            ),
        ),
        
        ExtStringField('variation1_attribute',
            required = 0,
            widget = atapi.StringWidget(
                label = _(u"label_variation1_attr", default=u"Variation 1 Attribute"),
                description = _(u"desc_variation1_attr", default=u""),
            ),
        ),
        
        ExtStringField('variation1_values',
            required = 0,
            widget = atapi.StringWidget(
                label = _(u"label_variation1_values", default=u"Variation 1 Values"),
                description = _(u"desc_variation1_values", default=u""),
            ),
        ),


        ExtStringField('variation2_attribute',
            required = 0,
            widget = atapi.StringWidget(
                label = _(u"label_variation2_attr", default=u"Variation 2 Attribute"),
                description = _(u"desc_variation2_attr", default=u""),
            ),
        ),
        
        
        ExtStringField('variation2_values',
            required = 0,
            widget = atapi.StringWidget(
                label = _(u"label_variation2_values", default=u"Variation 2 Values"),
                description = _(u"desc_variation2_values", default=u""),
            ),
        ),
         
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields
