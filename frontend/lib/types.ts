export type User = {
    id: number;
    full_name: string;
    email: string;
    phone: string | null;
    role: string;
    status: string;
  };
  
  export type Book = {
    id: number;
    isbn: string;
    title: string;
    subtitle: string | null;
    authors: string;
    description: string;
    summary: string;
    category: string;
    genre: string;
    language: string;
    publication_year: number;
    page_count: number;
    reading_level: string;
    cover_url: string | null;
    total_copies: number;
    available_copies: number;
    status: string;
  };
  
  export type BookList = {
    items: Book[];
    total: number;
    page: number;
    page_size: number;
    query: string | null;
    exact_match: boolean;
    message: string | null;
  };
  
  export type Rental = {
    id: number;
    book_id: number;
    book_title: string;
    authors: string;
    start_at: string | null;
    due_at: string;
    returned_at: string | null;
    status: string;
    days_remaining: number | null;
    days_overdue: number | null;
  };
  
  export type Dashboard = {
    full_name: string;
    active_count: number;
    max_allowed: number;
    remaining: number;
    capacity_message: string;
    current: Rental[];
    history: Rental[];
  };