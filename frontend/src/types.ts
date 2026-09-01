export interface User {
  id: string
  email: string
  name: string
  picture: string | null
  role: 'user' | 'admin'
}

export interface Order {
  id: string
  order_number: string
  customer_name: string
  order_date: string | null
  total_amount: string | null
  currency: string
  status: string
  notes: string | null
  source_filename: string
  raw_text: string
  extracted_data: Record<string, unknown>
  created_at: string
  updated_at: string
  owner: Pick<User, 'id' | 'email' | 'name'>
}

export interface OCRResult {
  upload_token: string
  filename: string
  raw_text: string
  lines: Array<{ text: string; confidence: number; box: unknown; page: number }>
  suggested: Record<string, string | number | null>
}

