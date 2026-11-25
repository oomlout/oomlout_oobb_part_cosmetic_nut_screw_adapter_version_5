$fn = 100;

difference() {
    cylinder(h=4.5, d=12);
    translate([0, 0, 2])
        cylinder(h=2.5, r=3.462, $fn=6);
    translate([0, 0, -1])
        cylinder(h=6.5, r=1.8);
}
