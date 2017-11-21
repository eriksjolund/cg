# Samples in 📤

One of the most central aspects of our dataflow is how we accept new samples into our system. It's imperative that this is handled in a unified way so that downstream automation can progress smoothly.

## Inputs

There's multiple ways to input sample information:

- **Excel orderform**
- **JSON LIMS export**
- **Web form**

## REST API

Once authenticated through _Google OAuth_, it's possible to submit samples to the [REST API][rest]. This process normally takes place in the [portal][portal] but it's entirely possible to obtain and use a valid OAuth token any other way. The REST server follows the **JSON web token** pattern and expects a header like this:

    Authorization: Bearer LONG_TOKEN_STRING

> Some endpoints don't require authentication, for example you can try accessing: [/api/v1/applications](https://clinical-api.scilifelab.se/api/v1/applications).

For every order that is processed through the portal, the original JSON payload is directly dumped in the server log. It's a good place to look if you are debugging an order where e.g. all samples weren't added to LIMS.

## Server-side validation

The "order portal" performs validation of the input data both on the client and the server. The server side validation is using [PySchemes][pyschemes]. The server will respond with a `401` JSON response if validation of the order fails with the error message included. The requirements of a valid order is defined per _order type_ (scout, microbial, etc.) in:

    /cg/meta/orders/schema.py

> we've seen some problems with optional fields that are filled in with `null` / `None` (empty) which makes the validation give an error. It's generally safe to update _optional_ fields with a custom `TypeValidator` where you can explicitly allow "empty" values.

## Client-side validation

We try to perform as much validation already in the client as possible. This is in order to make the form as responsive as possible to the end user.

Validation takes place inside the _Vuex_ `/store`, more specifically as part of the getters:

- **families**: "scout" and "external" orders
- **samples**: "fastq", "rml", and "microbial" orders

The validation is heavily customized to account for all the diffent possible combinations. For example `container_name` is a _required_ field if, and only if, `container` is "96 well plate".

The interface generally updates to display on the relevant fields for any given order type and combination of already filled-in values. Apart from the regular order types we also differentiate:

- **labOrder**: samples from which libraries are prepare internally
- **analysisOrder**: samples which are going to be analyzed and answered out in Scout

If existing samples are included in the order. They are differentiated based on the existance of a "internalId" property.

### Displaying errors

When any of the forms (order, family, sample) are saved by the user, the store is updated with the current results from the form. This triggers updates that are propagated via the _Vuex_-getters to the relevant components/templates.

To translate the boolean validity of any given required field + value (_Vuex_ getter) to the _Bootstrap + Vue_ "state" we follow this architecture.

1. Determine whether the required field is valid or not (true/false) in a _Vuex_ getter
1. Map the getter to a computed property in the component
1. Set another computed property to translate to a _Bootstrap_ state string
1. Use the computed property in the template

   ```html
   <b-form-input v-model="form.name" :state="nameState" />
   ```

[rest]: https://clinical-api.scilifelab.se/api
[portal]: https://clinical.scilifelab.se/
[pyschemes]: https://github.com/shivylp/pyschemes
