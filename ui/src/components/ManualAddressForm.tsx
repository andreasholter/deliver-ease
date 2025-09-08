import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Props {
  onSubmit: (postalCode: string) => void;
  isLoading: boolean;
}

const ManualAddressForm: React.FC<Props> = ({ onSubmit, isLoading }) => {
  const { t } = useTranslation();
  const [postalCode, setPostalCode] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (postalCode.length >= 4) {
      onSubmit(postalCode);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" style={{ fontFamily: 'Poppins, sans-serif', color: '#5d5c45' }}>
      <div className="space-y-2">
        <Input
          id="postal-code"
          type="tel"
          value={postalCode}
          onChange={(e) => setPostalCode(e.target.value)}
          placeholder="Postnummer"
          maxLength={4}
          required
          className="h-12 text-lg"
          style={{ color: '#5d5c45', fontFamily: 'Poppins, sans-serif' }}
        />
      </div>
      <Button 
        type="submit" 
        disabled={isLoading || postalCode.length < 4} 
        className="w-full h-12 text-white font-bold" 
        style={{ backgroundColor: '#5d5c45', fontFamily: 'Poppins, sans-serif' }}
      >
        {isLoading ? t("checkingButton") : t("checkButtonShort")}
      </Button>
    </form>
  );
};

export default ManualAddressForm;


