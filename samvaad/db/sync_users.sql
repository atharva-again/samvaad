-- Create a function to handle new user inserts
create or replace function public.handle_new_user()
returns trigger as $$
begin
  -- Explicitly cast UUID to text if needed, though Postgres usually handles it.
  -- Add basic error handling so we don't block the user signup if sync fails.
  begin
      insert into public.users (id, email)
      values (new.id::text, new.email)
      on conflict (id) do nothing;
  exception when others then
      -- Log the error (visible in Supabase logs) but don't fail the transaction
      -- warning: "User sync failed: " || SQLERRM;
      -- Actually, for now, let's Raise Warning so it doesn't rollback Auth
      raise warning 'User sync failed for %: %', new.id, SQLERRM;
  end;
  return new;
end;
$$ language plpgsql security definer;

-- Create the trigger to fire whenever a new user is created in auth.users
-- Drop first to allow re-running script
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
