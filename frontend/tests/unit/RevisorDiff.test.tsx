import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RevisorDiff } from '@/components/RevisorDiff';

describe('RevisorDiff', () => {
  it('compõe o texto final conforme a aceitação ou rejeição das sugestões', async () => {
    const onTextoFinalChange = vi.fn();
    render(
      <RevisorDiff antes="olá mundo" depois="oi mundo" onTextoFinalChange={onTextoFinalChange} />,
    );

    await waitFor(() => expect(onTextoFinalChange).toHaveBeenLastCalledWith('oi mundo'));

    await userEvent.click(screen.getByRole('button', { name: 'Rejeitar todas' }));
    await waitFor(() => expect(onTextoFinalChange).toHaveBeenLastCalledWith('olá mundo'));
  });

  it('informa quando não há alterações entre as versões', () => {
    render(<RevisorDiff antes="igual" depois="igual" />);
    expect(screen.getByText('Nenhuma alteração entre as versões.')).toBeInTheDocument();
  });
});
