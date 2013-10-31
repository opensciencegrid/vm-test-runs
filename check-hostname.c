#include <stdio.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

int main(int argc, char *argv[])
{
  struct hostent *host_entry;
  struct in_addr **addr_list;
  
  if (argc != 2) {
    printf("usage: check-hostname HOSTNAME\n");
    return 1;
  }

  printf("Checking gethostbyname(%s)... ", argv[1]);
  host_entry = gethostbyname(argv[1]);
  if (host_entry == NULL) {
    printf("returned NULL; h_errno = %d, %s\n", h_errno, hstrerror(h_errno));
    return 1;
  }
  addr_list = (struct in_addr **)host_entry->h_addr_list;
  printf("first addr is %s\n", inet_ntoa(*addr_list[0]));

  return 0;
}
