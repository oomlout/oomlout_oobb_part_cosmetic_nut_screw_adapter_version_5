$fn = 100;

difference() {
    cylinder(h=7, d=12);
    translate([0, 0, 2])
        cylinder(h=5, r=5.91425, $fn=6);
    translate([0, 0, -1])
        cylinder(h=9, r=3.25);
}
