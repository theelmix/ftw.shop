from archetypes.schemaextender.field import ExtensionField
from archetypes.schemaextender.interfaces import ISchemaExtender

from zope.component import adapts
from zope.interface import implements

from ftw.shop import shopMessageFactory as _
from ftw.shop.interfaces.shopitem import IShopItem
from ftw.shop.interfaces.shopitemvariant import IShopItemVariant

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
            widget = atapi.DecimalWidget(
                label = _(u"label_price", default=u"Price"),
                description = _(u"desc_price", default=u""),
                size=8,
            ),
        ),

        ExtStringField('skuCode',
            required = 1,
            widget = atapi.StringWidget(
                label = _(u"label_sku_code", default=u"SKU Code"),
                description = _(u"desc_sku_code", default=u""),
            ),
        ),
    ]

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return self.fields


class ShopItemVariantExtender(ShopItemExtender):
    """Extends ShopItemVariants with a `variantLabel` that denotes
    the attribute that varies (color, size, ...). ShopItemVariants then
    can be added to a ShopItem and will be grouped by `variantLabel`
    """
    implements(ISchemaExtender)
    adapts(IShopItemVariant)
    
    fields = ShopItemExtender.fields + [
        ExtStringField('variantLabel',
            searchable = 0,
            required = 0,
            widget = atapi.StringWidget(
                label = _(u"label_variant_label", default=u"Variant Label"),
                description = _(u"desc_variant_label", default=u"e.g. Color. All variant items with the same label will be grouped together."),
            ),
        ),
    ]
