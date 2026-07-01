import client from './client'

export const deliveryApi = {
  /** T3/FR-30: fetch the delivery email HTML template for client-side preview. */
  getTemplate: () => client.get<string>('/delivery/template'),
}
