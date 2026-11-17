# LC form: QR code vs AI reading (Gemini)

10 fake LC applications: 4 typed (filled on a computer, printed with the QR code) and 6 handwritten (printed blank, filled by hand: no QR code). Scan quality clean / medium / poor. Accuracy = answers read exactly right / answers on the form; formatting differences (case, spaces, 6/11/2026 vs 06/11/2026, 1,000.00 vs 1000.00) don't count as errors. Wrong = a different answer; missed = an answer not read; invented = an answer read from a blank question.

## Summary

| Reader | Forms read | Forms 100% correct | Accuracy min | median | max | average (all answers) | Seconds min | median | max | average |
|---|---|---|---|---|---|---|---|---|---|---|
| QR code | 4 | 4 of 4 | 100.0% | 100.0% | 100.0% | 100.0% | 0.0 | 0.0 | 0.1 | 0.0 |
| gemini-3.7-flash | 10 | 8 of 10 | 96.6% | 100.0% | 100.0% | 99.5% | 22.4 | 31.5 | 76.1 | 38.7 |

QR codes exist only on forms filled on a computer, so the QR row covers the 4 typed forms.

## Each form

| Form | Filled | Scan | Answers | QR code: correct / errors / 100%? / s | gemini-3.7-flash: correct / errors / 100%? / s |
|---|---|---|---|---|---|
| 01 | typed | clean | 58 | 58/58 (100.0%) / 0 / YES / 0.061 | 58/58 (100.0%) / 0 / YES / 72.79 |
| 02 | typed | clean | 51 | 51/51 (100.0%) / 0 / YES / 0.048 | 51/51 (100.0%) / 0 / YES / 34.12 |
| 03 | typed | medium | 65 | 65/65 (100.0%) / 0 / YES / 0.028 | 65/65 (100.0%) / 0 / YES / 33.82 |
| 04 | typed | poor | 58 | 58/58 (100.0%) / 0 / YES / 0.015 | 56/58 (96.6%) / 2 / no / 41.35 |
| 05 | handwritten | clean | 69 | no QR code | 69/69 (100.0%) / 0 / YES / 23.14 |
| 06 | handwritten | clean | 57 | no QR code | 57/57 (100.0%) / 0 / YES / 76.14 |
| 07 | handwritten | medium | 56 | no QR code | 56/56 (100.0%) / 0 / YES / 22.38 |
| 08 | handwritten | medium | 63 | no QR code | 63/63 (100.0%) / 0 / YES / 27.02 |
| 09 | handwritten | poor | 71 | no QR code | 70/71 (98.6%) / 1 / no / 29.18 |
| 10 | handwritten | poor | 54 | no QR code | 54/54 (100.0%) / 0 / YES / 26.84 |

## QR code: by type of form and scan

| Group | Forms | 100% correct | Accuracy | Errors | Average seconds |
|---|---|---|---|---|---|
| typed-clean | 2 | 2 | 100.0% | 0 | 0.1 |
| typed-medium | 1 | 1 | 100.0% | 0 | 0.0 |
| typed-poor | 1 | 1 | 100.0% | 0 | 0.0 |

## QR code: by kind of answer

| Kind | Answers | Correct | Accuracy |
|---|---|---|---|
| date | 11 | 11 | 100.0% |
| radio | 38 | 38 | 100.0% |
| text | 69 | 69 | 100.0% |
| phone | 10 | 10 | 100.0% |
| select | 11 | 11 | 100.0% |
| amount | 4 | 4 | 100.0% |
| check | 38 | 38 | 100.0% |
| number | 35 | 35 | 100.0% |
| checks | 3 | 3 | 100.0% |
| long | 6 | 6 | 100.0% |
| account | 7 | 7 | 100.0% |

## QR code: by data field

84 fields were answered on at least one form. Field accuracy: min 100.0%, median 100.0%, max 100.0%, average 100.0%. 84 of 84 fields were read right on every form. Worst fields first:

| # | Field (id) | Question | Forms answered | Correct | Accuracy | Invented on blank forms |
|---|---|---|---|---|---|---|
| 1.1 | `application_date` | Date | 4 | 4 | 100% |  |
| 10.1 | `partial_shipment` | Partial shipment | 4 | 4 | 100% |  |
| 10.2 | `transhipment` | Transhipment | 4 | 4 | 100% |  |
| 10.3 | `shipment_from` | Shipment from | 1 | 1 | 100% |  |
| 10.4 | `shipment_from_place` | Shipment from: place | 3 | 3 | 100% |  |
| 10.6 | `shipment_to` | Shipment to | 2 | 2 | 100% |  |
| 10.7 | `shipment_to_place` | Shipment to: place | 4 | 4 | 100% |  |
| 10.9 | `latest_shipment_date` | Latest shipment date | 3 | 3 | 100% |  |
| 11.1 | `expiry_date` | Date of expiry (in beneficiary's country) | 4 | 4 | 100% |  |
| 11.2 | `presentation_days` | Presentation period (days after shipment) | 3 | 3 | 100% |  |
| 12.1 | `back_to_back` | This is a back-to-back DC to be issued against the master cr | 1 | 1 | 100% |  |
| 12.2 | `master_dc_no` | Master credit no | 1 | 1 | 100% |  |
| 12.3 | `master_dc_issued_by` | Issued by | 1 | 1 | 100% |  |
| 13.1 | `drafts` | Drafts for the percentage of invoice value below, at | 3 | 3 | 100% |  |
| 13.2 | `drafts_percent` | Percentage of invoice value (%) | 3 | 3 | 100% |  |
| 13.3 | `drafts_at` | Drafts at | 3 | 3 | 100% |  |
| 13.4 | `term_days` | Term: days | 2 | 2 | 100% |  |
| 13.5 | `term_after` | days after | 2 | 2 | 100% |  |
| 13.7 | `term_prepay` | If it is a term LC, please select one | 2 | 2 | 100% |  |
| 14.1 | `doc_bill_of_lading` | Full set of Clean on Board marine bills of lading | 3 | 3 | 100% |  |
| 14.10 | `do_originals` | Delivery order: originals | 2 | 2 | 100% |  |
| 14.11 | `do_copies` | Delivery order: copies | 2 | 2 | 100% |  |
| 14.12 | `do_countersigned_by` | Countersigned by how many of our signatories | 2 | 2 | 100% |  |
| 14.13 | `do_signature_verified` | Whose signature(s) ... to be verified by the Bank | 2 | 2 | 100% |  |
| 14.18 | `doc_beneficiary_certificate` | Beneficiary's certificate stating 1 set of non-negotiable do | 3 | 3 | 100% |  |
| 14.19 | `bencert_sent_by` | Sent by | 3 | 3 | 100% |  |
| 14.2 | `bl_made_out_to` | Made out to | 3 | 3 | 100% |  |
| 14.20 | `bencert_days` | Within (days after shipment) | 3 | 3 | 100% |  |
| 14.21 | `doc_commercial_invoice` | Signed commercial invoice | 3 | 3 | 100% |  |
| 14.22 | `invoice_originals` | Commercial invoice: originals | 3 | 3 | 100% |  |
| 14.23 | `invoice_copies` | Commercial invoice: copies | 3 | 3 | 100% |  |
| 14.24 | `doc_packing_list` | Packing list | 2 | 2 | 100% |  |
| 14.25 | `packing_list_originals` | Packing list: originals | 2 | 2 | 100% |  |
| 14.26 | `packing_list_copies` | Packing list: copies | 2 | 2 | 100% |  |
| 14.27 | `doc_weight_note` | Weight note | 2 | 2 | 100% |  |
| 14.28 | `weight_note_originals` | Weight note: originals | 2 | 2 | 100% |  |
| 14.29 | `weight_note_copies` | Weight note: copies | 2 | 2 | 100% |  |
| 14.3 | `bl_made_out_to_other` | Made out to (other) | 2 | 2 | 100% |  |
| 14.34 | `doc_other` | Other documents | 2 | 2 | 100% |  |
| 14.35 | `other_documents_1` | Other documents | 2 | 2 | 100% |  |
| 14.4 | `bl_freight` | Marked Freight | 3 | 3 | 100% |  |
| 14.5 | `bl_notify_party` | Notify party (if not specified, notify party is considered t | 3 | 3 | 100% |  |
| 14.6 | `doc_air_waybill` | Original Air Waybill consigned to the Bank | 2 | 2 | 100% |  |
| 14.7 | `awb_freight` | Marked Freight | 2 | 2 | 100% |  |
| 14.8 | `awb_notify_party` | Notify party (if not specified, notify party is considered t | 2 | 2 | 100% |  |
| 14.9 | `doc_delivery_order` | Delivery order signed by beneficiary made out to applicant | 2 | 2 | 100% |  |
| 15.1 | `goods_description` | Goods description (if space is insufficient, attach addition | 4 | 4 | 100% |  |
| 16.1 | `additional_conditions` | Additional conditions (if space is insufficient, attach addi | 2 | 2 | 100% |  |
| 17.1 | `bank_charges` | All bank charges are for account of | 4 | 4 | 100% |  |
| 17.10 | `advance_payment_account` | Account no for advance payment | 3 | 3 | 100% |  |
| 17.11 | `debit_issuance_charges` | Please debit all DC issuance charges to our account with you | 2 | 2 | 100% |  |
| 17.12 | `issuance_charges_account` | Account no for DC issuance charges | 4 | 4 | 100% |  |
| 17.2 | `bank_charges_for` | Charges for account of | 4 | 4 | 100% |  |
| 17.3 | `confirmation` | Confirmation required | 1 | 1 | 100% |  |
| 17.4 | `confirmation_charges` | Confirmation charges | 1 | 1 | 100% |  |
| 17.5 | `post_shipment_financing` | Please provide us with post-shipment financing under Documen | 2 | 2 | 100% |  |
| 17.6 | `financing_type` | Financing | 2 | 2 | 100% |  |
| 17.8 | `forward_contract_no` | Forward contract no | 1 | 1 | 100% |  |
| 17.9 | `advance_payment` | We authorise you to debit DC amount in full from our account | 3 | 3 | 100% |  |
| 18.1 | `authorised_person` | Name and title of authorised person(s) | 3 | 3 | 100% |  |
| 2.1 | `mode_of_advising` | Mode of advising | 4 | 4 | 100% |  |
| 3.1 | `applicant_name` | Applicant name | 4 | 4 | 100% |  |
| 3.2 | `applicant_address_1` | Applicant address | 4 | 4 | 100% |  |
| 3.3 | `applicant_address_2` | Applicant address (line 2) | 4 | 4 | 100% |  |
| 3.6 | `contact_name` | Contact party for this application & confirmation of FX rate | 4 | 4 | 100% |  |
| 3.7 | `contact_tel` | Contact party: Tel no | 4 | 4 | 100% |  |
| 3.8 | `contact_fax` | Contact party: Fax no | 2 | 2 | 100% |  |
| 5.1 | `advising_bank_name` | Name | 3 | 3 | 100% |  |
| 5.2 | `advising_bank_address_1` | Address | 1 | 1 | 100% |  |
| 5.3 | `advising_bank_address_2` | Address (line 2) | 4 | 4 | 100% |  |
| 7.1 | `beneficiary_name` | Beneficiary's name | 4 | 4 | 100% |  |
| 7.2 | `beneficiary_address_1` | Beneficiary's address | 4 | 4 | 100% |  |
| 7.3 | `beneficiary_address_2` | Beneficiary's address (line 2) | 3 | 3 | 100% |  |
| 7.4 | `beneficiary_address_3` | Beneficiary's address (line 3) | 4 | 4 | 100% |  |
| 7.5 | `beneficiary_address_4` | Beneficiary's address (line 4) | 2 | 2 | 100% |  |
| 7.6 | `beneficiary_contact` | Contact person | 4 | 4 | 100% |  |
| 7.7 | `beneficiary_tel` | Tel no | 4 | 4 | 100% |  |
| 8.1 | `currency` | Currency | 4 | 4 | 100% |  |
| 8.2 | `amount` | Amount | 4 | 4 | 100% |  |
| 8.3 | `gst` | For local DCs, amount is (if not checked, it will be inclusi | 2 | 2 | 100% |  |
| 8.4 | `tolerance` | Tolerance on credit amount & goods quantity | 3 | 3 | 100% |  |
| 8.5 | `tolerance_plus` | Tolerance + (%) | 3 | 3 | 100% |  |
| 8.6 | `tolerance_minus` | Tolerance - (%) | 3 | 3 | 100% |  |
| 9.1 | `price_basis` | Price basis | 4 | 4 | 100% |  |

## QR code: every error

None.

## gemini-3.7-flash: by type of form and scan

| Group | Forms | 100% correct | Accuracy | Errors | Average seconds |
|---|---|---|---|---|---|
| hand-clean | 2 | 2 | 100.0% | 0 | 49.6 |
| hand-medium | 2 | 2 | 100.0% | 0 | 24.7 |
| hand-poor | 2 | 1 | 99.2% | 1 | 28.0 |
| typed-clean | 2 | 2 | 100.0% | 0 | 53.5 |
| typed-medium | 1 | 1 | 100.0% | 0 | 33.8 |
| typed-poor | 1 | 0 | 96.6% | 2 | 41.4 |

## gemini-3.7-flash: by kind of answer

| Kind | Answers | Correct | Accuracy |
|---|---|---|---|
| radio | 92 | 89 | 96.7% |
| date | 25 | 25 | 100.0% |
| text | 176 | 176 | 100.0% |
| phone | 26 | 26 | 100.0% |
| select | 40 | 40 | 100.0% |
| amount | 10 | 10 | 100.0% |
| check | 100 | 100 | 100.0% |
| number | 96 | 96 | 100.0% |
| checks | 6 | 6 | 100.0% |
| long | 16 | 16 | 100.0% |
| account | 15 | 15 | 100.0% |

## gemini-3.7-flash: by data field

93 fields were answered on at least one form. Field accuracy: min 80.0%, median 100.0%, max 100.0%, average 99.5%. 90 of 93 fields were read right on every form. Worst fields first:

| # | Field (id) | Question | Forms answered | Correct | Accuracy | Invented on blank forms |
|---|---|---|---|---|---|---|
| 13.7 | `term_prepay` | If it is a term LC, please select one | 5 | 4 | 80% |  |
| 8.3 | `gst` | For local DCs, amount is (if not checked, it will be inclusi | 6 | 5 | 83% |  |
| 9.1 | `price_basis` | Price basis | 10 | 9 | 90% |  |
| 1.1 | `application_date` | Date | 10 | 10 | 100% |  |
| 10.1 | `partial_shipment` | Partial shipment | 10 | 10 | 100% |  |
| 10.2 | `transhipment` | Transhipment | 10 | 10 | 100% |  |
| 10.3 | `shipment_from` | Shipment from | 6 | 6 | 100% |  |
| 10.4 | `shipment_from_place` | Shipment from: place | 9 | 9 | 100% |  |
| 10.6 | `shipment_to` | Shipment to | 7 | 7 | 100% |  |
| 10.7 | `shipment_to_place` | Shipment to: place | 9 | 9 | 100% |  |
| 10.9 | `latest_shipment_date` | Latest shipment date | 5 | 5 | 100% |  |
| 11.1 | `expiry_date` | Date of expiry (in beneficiary's country) | 10 | 10 | 100% |  |
| 11.2 | `presentation_days` | Presentation period (days after shipment) | 7 | 7 | 100% |  |
| 12.1 | `back_to_back` | This is a back-to-back DC to be issued against the master cr | 5 | 5 | 100% |  |
| 12.2 | `master_dc_no` | Master credit no | 5 | 5 | 100% |  |
| 12.3 | `master_dc_issued_by` | Issued by | 5 | 5 | 100% |  |
| 13.1 | `drafts` | Drafts for the percentage of invoice value below, at | 6 | 6 | 100% |  |
| 13.2 | `drafts_percent` | Percentage of invoice value (%) | 6 | 6 | 100% |  |
| 13.3 | `drafts_at` | Drafts at | 6 | 6 | 100% |  |
| 13.4 | `term_days` | Term: days | 5 | 5 | 100% |  |
| 13.5 | `term_after` | days after | 5 | 5 | 100% |  |
| 14.1 | `doc_bill_of_lading` | Full set of Clean on Board marine bills of lading | 6 | 6 | 100% |  |
| 14.10 | `do_originals` | Delivery order: originals | 6 | 6 | 100% |  |
| 14.11 | `do_copies` | Delivery order: copies | 6 | 6 | 100% |  |
| 14.12 | `do_countersigned_by` | Countersigned by how many of our signatories | 6 | 6 | 100% |  |
| 14.13 | `do_signature_verified` | Whose signature(s) ... to be verified by the Bank | 6 | 6 | 100% |  |
| 14.14 | `doc_insurance` | Marine/Air Insurance Policy or Certificate in duplicate, in  | 4 | 4 | 100% |  |
| 14.15 | `insurance_arrangement` | For FOB/CFR/FCA/CPT | 3 | 3 | 100% |  |
| 14.16 | `insurance_cover_no` | Open cover no | 2 | 2 | 100% |  |
| 14.17 | `insurance_cover_with` | With | 2 | 2 | 100% |  |
| 14.18 | `doc_beneficiary_certificate` | Beneficiary's certificate stating 1 set of non-negotiable do | 6 | 6 | 100% |  |
| 14.19 | `bencert_sent_by` | Sent by | 6 | 6 | 100% |  |
| 14.2 | `bl_made_out_to` | Made out to | 6 | 6 | 100% |  |
| 14.20 | `bencert_days` | Within (days after shipment) | 6 | 6 | 100% |  |
| 14.21 | `doc_commercial_invoice` | Signed commercial invoice | 7 | 7 | 100% |  |
| 14.22 | `invoice_originals` | Commercial invoice: originals | 7 | 7 | 100% |  |
| 14.23 | `invoice_copies` | Commercial invoice: copies | 7 | 7 | 100% |  |
| 14.24 | `doc_packing_list` | Packing list | 6 | 6 | 100% |  |
| 14.25 | `packing_list_originals` | Packing list: originals | 6 | 6 | 100% |  |
| 14.26 | `packing_list_copies` | Packing list: copies | 6 | 6 | 100% |  |
| 14.27 | `doc_weight_note` | Weight note | 6 | 6 | 100% |  |
| 14.28 | `weight_note_originals` | Weight note: originals | 6 | 6 | 100% |  |
| 14.29 | `weight_note_copies` | Weight note: copies | 6 | 6 | 100% |  |
| 14.3 | `bl_made_out_to_other` | Made out to (other) | 4 | 4 | 100% |  |
| 14.30 | `doc_certificate_of_origin` | Certificate of origin | 4 | 4 | 100% |  |
| 14.31 | `origin_originals` | Certificate of origin: originals | 4 | 4 | 100% |  |
| 14.32 | `origin_copies` | Certificate of origin: copies | 4 | 4 | 100% |  |
| 14.33 | `origin_country` | Showing country of origin as | 4 | 4 | 100% |  |
| 14.34 | `doc_other` | Other documents | 4 | 4 | 100% |  |
| 14.35 | `other_documents_1` | Other documents | 4 | 4 | 100% |  |
| 14.4 | `bl_freight` | Marked Freight | 6 | 6 | 100% |  |
| 14.5 | `bl_notify_party` | Notify party (if not specified, notify party is considered t | 6 | 6 | 100% |  |
| 14.6 | `doc_air_waybill` | Original Air Waybill consigned to the Bank | 4 | 4 | 100% |  |
| 14.7 | `awb_freight` | Marked Freight | 4 | 4 | 100% |  |
| 14.8 | `awb_notify_party` | Notify party (if not specified, notify party is considered t | 4 | 4 | 100% |  |
| 14.9 | `doc_delivery_order` | Delivery order signed by beneficiary made out to applicant | 6 | 6 | 100% |  |
| 15.1 | `goods_description` | Goods description (if space is insufficient, attach addition | 10 | 10 | 100% |  |
| 16.1 | `additional_conditions` | Additional conditions (if space is insufficient, attach addi | 6 | 6 | 100% |  |
| 17.1 | `bank_charges` | All bank charges are for account of | 10 | 10 | 100% |  |
| 17.10 | `advance_payment_account` | Account no for advance payment | 5 | 5 | 100% |  |
| 17.11 | `debit_issuance_charges` | Please debit all DC issuance charges to our account with you | 5 | 5 | 100% |  |
| 17.12 | `issuance_charges_account` | Account no for DC issuance charges | 10 | 10 | 100% |  |
| 17.2 | `bank_charges_for` | Charges for account of | 10 | 10 | 100% |  |
| 17.3 | `confirmation` | Confirmation required | 4 | 4 | 100% |  |
| 17.4 | `confirmation_charges` | Confirmation charges | 4 | 4 | 100% |  |
| 17.5 | `post_shipment_financing` | Please provide us with post-shipment financing under Documen | 5 | 5 | 100% |  |
| 17.6 | `financing_type` | Financing | 5 | 5 | 100% |  |
| 17.7 | `financing_currency` | Foreign currency financing in (type of currency) | 2 | 2 | 100% |  |
| 17.8 | `forward_contract_no` | Forward contract no | 2 | 2 | 100% |  |
| 17.9 | `advance_payment` | We authorise you to debit DC amount in full from our account | 5 | 5 | 100% |  |
| 18.1 | `authorised_person` | Name and title of authorised person(s) | 7 | 7 | 100% |  |
| 2.1 | `mode_of_advising` | Mode of advising | 10 | 10 | 100% |  |
| 3.1 | `applicant_name` | Applicant name | 10 | 10 | 100% |  |
| 3.2 | `applicant_address_1` | Applicant address | 10 | 10 | 100% |  |
| 3.3 | `applicant_address_2` | Applicant address (line 2) | 9 | 9 | 100% |  |
| 3.6 | `contact_name` | Contact party for this application & confirmation of FX rate | 10 | 10 | 100% |  |
| 3.7 | `contact_tel` | Contact party: Tel no | 10 | 10 | 100% |  |
| 3.8 | `contact_fax` | Contact party: Fax no | 7 | 7 | 100% |  |
| 5.1 | `advising_bank_name` | Name | 7 | 7 | 100% |  |
| 5.2 | `advising_bank_address_1` | Address | 5 | 5 | 100% |  |
| 5.3 | `advising_bank_address_2` | Address (line 2) | 9 | 9 | 100% |  |
| 7.1 | `beneficiary_name` | Beneficiary's name | 10 | 10 | 100% |  |
| 7.2 | `beneficiary_address_1` | Beneficiary's address | 10 | 10 | 100% |  |
| 7.3 | `beneficiary_address_2` | Beneficiary's address (line 2) | 7 | 7 | 100% |  |
| 7.4 | `beneficiary_address_3` | Beneficiary's address (line 3) | 9 | 9 | 100% |  |
| 7.5 | `beneficiary_address_4` | Beneficiary's address (line 4) | 5 | 5 | 100% |  |
| 7.6 | `beneficiary_contact` | Contact person | 7 | 7 | 100% |  |
| 7.7 | `beneficiary_tel` | Tel no | 9 | 9 | 100% |  |
| 8.1 | `currency` | Currency | 10 | 10 | 100% |  |
| 8.2 | `amount` | Amount | 10 | 10 | 100% |  |
| 8.4 | `tolerance` | Tolerance on credit amount & goods quantity | 7 | 7 | 100% |  |
| 8.5 | `tolerance_plus` | Tolerance + (%) | 7 | 7 | 100% |  |
| 8.6 | `tolerance_minus` | Tolerance - (%) | 7 | 7 | 100% |  |

## gemini-3.7-flash: every error

- 04-typed-poor `gst` wrong: true "inclusive of GST" -> read "No GST"
- 04-typed-poor `price_basis` missed: true "CPT" -> read null
- 09-hand-poor `term_prepay` missed: true "You may not prepay the acceptance of this term LC" -> read null
