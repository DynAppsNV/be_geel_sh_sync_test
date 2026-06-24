.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
  :target: https://www.gnu.org/licenses/agpl
  :alt: License: AGPL-3

===================================
DynApps Dashboard Smartbutton Mixin
===================================

**DynApps Dashboard Smartbutton Mixin** is an extension module that
seamlessly integrates dashboard access directly into Odoo form views
through smart buttons. This module provides a reusable mixin that
automatically adds dashboard smart buttons to any model's form view,
enabling quick access to relevant analytics without leaving the current
record.

Key Features:
-------------

-  **Abstract Mixin Model**: Easily add dashboard integration to any
   Odoo model by inheriting ``dashboard.smart.button.mixin``
-  **Automatic Smart Button Injection**: Dynamically injects dashboard
   buttons into form views without manual XML modifications
-  **Context-Aware Dashboards**: Smart buttons automatically filter
   dashboard data based on the current record
-  **Multi-Dashboard Support**: Display multiple dashboard buttons when
   several dashboards are configured for the same model
-  **Custom Icons**: Support for configurable Font Awesome icons for
   each dashboard button
-  **Seamless Navigation**: Opens dashboards with pre-filtered context
   showing data relevant to the current record

How It Works:
-------------

1. Dashboards configured with specific models automatically appear as
   smart buttons on those model's form views
2. Clicking a smart button opens the associated dashboard with filters
   applied to show data related to the current record
3. The mixin uses view inheritance to inject buttons into the button_box
   area (or creates one if it doesn't exist)
4. Each dashboard can have a custom icon and label for easy
   identification

Technical Implementation:
-------------------------

-  **View Inheritance Override**: Uses ``_get_view()`` method override
   to inject smart buttons at runtime
-  **XML Generation**: Dynamically creates button XML elements using
   lxml
-  **Context Management**: Passes ``odoo_record_id`` in context to
   filter dashboard data
-  **Model Detection**: Automatically discovers dashboards configured
   for the current model

Use Cases:
----------

-  Add sales analytics buttons to customer form views
-  Display invoice analysis on partner records
-  Show inventory metrics on product forms
-  Integrate project dashboards into task views
-  Connect HR analytics to employee records

Integration Example:
--------------------

.. code:: python

   class ResPartner(models.Model):
       _name = 'res.partner'
       _inherit = ['res.partner', 'dashboard.smart.button.mixin']


Credits
=======

Maintainer
----------

.. image:: /dyn_dashboard_smartbutton/static/description/icon.png
  :alt: Dynapps
  :target: https://www.dynapps.eu
  :width: 88
  :height: 88

This module is maintained by Dynapps.